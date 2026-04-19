"""YouTube + Twitch OAuth and publish service.

Graceful mock fallback pattern: when provider env vars are missing/blank, every
function returns `mock=True` sentinel objects so the rest of the app keeps
working unchanged.

Environment variables (see `/app/backend/.env.example`):
  YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REDIRECT_URI
  TWITCH_CLIENT_ID  / TWITCH_CLIENT_SECRET  / TWITCH_REDIRECT_URI
"""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from core.crypto import vault_decrypt, vault_encrypt
from core.db import db
from core.helpers import now_iso

logger = logging.getLogger(__name__)

YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_USERS_URL = "https://api.twitch.tv/helix/users"
TWITCH_VIDEOS_URL = "https://api.twitch.tv/helix/videos"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
TWITCH_SCOPES = ["clips:edit", "channel:manage:videos", "user:read:email"]


def _env(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def provider_configured(provider: str) -> bool:
    if provider == "youtube":
        return bool(_env("YOUTUBE_CLIENT_ID") and _env("YOUTUBE_CLIENT_SECRET"))
    if provider == "twitch":
        return bool(_env("TWITCH_CLIENT_ID") and _env("TWITCH_CLIENT_SECRET"))
    return False


def _provider_cfg(provider: str) -> Dict[str, str]:
    p = provider.upper()
    return {
        "client_id": _env(f"{p}_CLIENT_ID"),
        "client_secret": _env(f"{p}_CLIENT_SECRET"),
        "redirect_uri": _env(f"{p}_REDIRECT_URI"),
    }


# -----------------------------------------------------------------------------
# AUTH URL BUILDING + STATE TOKENS
# -----------------------------------------------------------------------------
def build_auth_url(provider: str, state: str) -> Optional[str]:
    if not provider_configured(provider):
        return None
    cfg = _provider_cfg(provider)
    if provider == "youtube":
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",            # force refresh_token every time
            "include_granted_scopes": "true",
            "state": state,
        }
        return f"{YOUTUBE_AUTH_URL}?{urlencode(params)}"
    if provider == "twitch":
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(TWITCH_SCOPES),
            "state": state,
            "force_verify": "false",
        }
        return f"{TWITCH_AUTH_URL}?{urlencode(params)}"
    return None


async def create_state(user_id: str, provider: str) -> str:
    """Random CSRF state, stored in Mongo with 10-min TTL. Returns the state value."""
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": user_id,
        "provider": provider,
        "created_at": now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    })
    return state


async def consume_state(state: str, provider: str) -> Optional[str]:
    """Return user_id bound to the state, or None if invalid/expired."""
    doc = await db.oauth_states.find_one_and_delete({"state": state, "provider": provider})
    if not doc:
        return None
    if doc.get("expires_at") and doc["expires_at"] < now_iso():
        return None
    return doc.get("user_id")


# -----------------------------------------------------------------------------
# TOKEN EXCHANGE + REFRESH
# -----------------------------------------------------------------------------
async def exchange_code(provider: str, code: str) -> Dict[str, Any]:
    cfg = _provider_cfg(provider)
    if provider == "youtube":
        data = {
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": cfg["redirect_uri"],
            "grant_type": "authorization_code",
        }
        url = YOUTUBE_TOKEN_URL
    elif provider == "twitch":
        data = {
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": cfg["redirect_uri"],
            "grant_type": "authorization_code",
        }
        url = TWITCH_TOKEN_URL
    else:
        raise ValueError(f"Unknown provider {provider}")

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, data=data)
        r.raise_for_status()
        return r.json()


async def refresh_access_token(provider: str, refresh_token: str) -> Dict[str, Any]:
    cfg = _provider_cfg(provider)
    url = YOUTUBE_TOKEN_URL if provider == "youtube" else TWITCH_TOKEN_URL
    data = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, data=data)
        r.raise_for_status()
        return r.json()


async def fetch_provider_profile(provider: str, access_token: str) -> Dict[str, str]:
    async with httpx.AsyncClient(timeout=15) as client:
        if provider == "youtube":
            r = await client.get(
                f"{YOUTUBE_CHANNELS_URL}?part=snippet&mine=true",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r.raise_for_status()
            item = (r.json().get("items") or [{}])[0]
            return {
                "provider_user_id": item.get("id", ""),
                "display_name": (item.get("snippet") or {}).get("title", ""),
            }
        if provider == "twitch":
            cfg = _provider_cfg(provider)
            r = await client.get(
                TWITCH_USERS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Client-Id": cfg["client_id"],
                },
            )
            r.raise_for_status()
            item = (r.json().get("data") or [{}])[0]
            return {
                "provider_user_id": item.get("id", ""),
                "display_name": item.get("display_name", ""),
            }
    return {}


# -----------------------------------------------------------------------------
# CONNECTION PERSISTENCE (refresh_token encrypted at rest)
# -----------------------------------------------------------------------------
async def save_connection(user_id: str, provider: str, tokens: Dict[str, Any],
                          profile: Dict[str, str]) -> None:
    expires_in = int(tokens.get("expires_in", 3600))
    await db.oauth_connections.update_one(
        {"user_id": user_id, "provider": provider},
        {"$set": {
            "user_id": user_id,
            "provider": provider,
            "access_token_enc": vault_encrypt(tokens["access_token"]),
            "refresh_token_enc": vault_encrypt(tokens.get("refresh_token", "")),
            "access_expires_at": (datetime.now(timezone.utc)
                                  + timedelta(seconds=expires_in)).isoformat(),
            "provider_user_id": profile.get("provider_user_id"),
            "display_name": profile.get("display_name"),
            "updated_at": now_iso(),
        }, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )


async def get_connection(user_id: str, provider: str) -> Optional[Dict[str, Any]]:
    doc = await db.oauth_connections.find_one(
        {"user_id": user_id, "provider": provider}, {"_id": 0}
    )
    return doc


async def list_connections(user_id: str) -> Dict[str, Any]:
    rows = await db.oauth_connections.find(
        {"user_id": user_id},
        {"_id": 0, "access_token_enc": 0, "refresh_token_enc": 0},
    ).to_list(10)
    return {
        "connections": rows,
        "available_providers": [
            {"id": "youtube", "configured": provider_configured("youtube")},
            {"id": "twitch", "configured": provider_configured("twitch")},
        ],
    }


async def delete_connection(user_id: str, provider: str) -> bool:
    res = await db.oauth_connections.delete_one(
        {"user_id": user_id, "provider": provider}
    )
    return res.deleted_count > 0


async def ensure_valid_access_token(user_id: str, provider: str) -> Optional[str]:
    """Return a valid access token, refreshing if needed. None if not connected."""
    conn = await get_connection(user_id, provider)
    if not conn:
        return None
    expires_at = conn.get("access_expires_at")
    # Refresh 60s before actual expiry
    if expires_at and expires_at > (
        datetime.now(timezone.utc) + timedelta(seconds=60)
    ).isoformat():
        return vault_decrypt(conn["access_token_enc"])

    refresh_plain = vault_decrypt(conn.get("refresh_token_enc", ""))
    if not refresh_plain:
        return None
    try:
        fresh = await refresh_access_token(provider, refresh_plain)
    except httpx.HTTPError as e:
        logger.warning("OAuth refresh failed for %s/%s: %s", provider, user_id, e)
        return None
    expires_in = int(fresh.get("expires_in", 3600))
    update: Dict[str, Any] = {
        "access_token_enc": vault_encrypt(fresh["access_token"]),
        "access_expires_at": (datetime.now(timezone.utc)
                              + timedelta(seconds=expires_in)).isoformat(),
        "updated_at": now_iso(),
    }
    if fresh.get("refresh_token"):
        update["refresh_token_enc"] = vault_encrypt(fresh["refresh_token"])
    await db.oauth_connections.update_one(
        {"user_id": user_id, "provider": provider}, {"$set": update}
    )
    return fresh["access_token"]


# -----------------------------------------------------------------------------
# PUBLISH — metadata-only by default (resumable upload path is available upstream
# for future iteration; we keep this focused and small).
# -----------------------------------------------------------------------------
async def publish_to_youtube(user_id: str, title: str, description: str,
                             tags: list, privacy: str = "unlisted") -> Dict[str, Any]:
    token = await ensure_valid_access_token(user_id, "youtube")
    if not token:
        return {"mock": True, "reason": "not_connected",
                "url": f"https://studio.youtube.com/channel/UC_mock?upload={title.replace(' ', '+')}"}
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy, "embeddable": True, "license": "youtube"},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{YOUTUBE_VIDEOS_URL}?part=snippet,status",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
    if r.status_code not in (200, 201):
        logger.error("YouTube publish failed: %s %s", r.status_code, r.text)
        return {"mock": True, "reason": f"publish_failed_{r.status_code}",
                "url": "https://studio.youtube.com/"}
    video_id = r.json().get("id")
    return {"mock": False, "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}"}


async def publish_to_twitch(user_id: str, title: str, description: str) -> Dict[str, Any]:
    """Twitch doesn't let apps upload raw VODs — we list the broadcaster's videos
    so the streamer sees confirmation of their channel link. Clip creation is
    available as a separate action."""
    token = await ensure_valid_access_token(user_id, "twitch")
    conn = await get_connection(user_id, "twitch")
    if not token or not conn:
        return {"mock": True, "reason": "not_connected",
                "url": "https://www.twitch.tv/"}
    cfg = _provider_cfg("twitch")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            TWITCH_VIDEOS_URL,
            params={"user_id": conn["provider_user_id"], "first": 5, "type": "archive"},
            headers={"Authorization": f"Bearer {token}", "Client-Id": cfg["client_id"]},
        )
    if r.status_code != 200:
        return {"mock": True, "reason": f"twitch_api_{r.status_code}",
                "url": f"https://www.twitch.tv/{conn.get('display_name', '')}"}
    return {
        "mock": False,
        "note": "Linked; Twitch does not accept raw VOD uploads via API",
        "url": f"https://www.twitch.tv/{conn.get('display_name', '')}",
        "videos_recent": len(r.json().get("data", [])),
    }
