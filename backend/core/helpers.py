"""Cross-cutting helpers: notifications, anomaly alerts, recovery codes,
settings + time utilities."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt

from .constants import DEFAULT_SETTINGS
from .db import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_referral_code(name: str, user_id: str) -> str:
    """Short referral code based on name + uuid prefix."""
    prefix = ''.join([c for c in (name or '').upper() if c.isalnum()])[:4] or "VC"
    suffix = user_id.replace("-", "")[:6].upper()
    return f"{prefix}{suffix}"


async def get_settings() -> Dict[str, Any]:
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        doc = {"id": "global", **DEFAULT_SETTINGS, "updated_at": now_iso()}
        await db.settings.insert_one(doc.copy())
        return doc
    return {**DEFAULT_SETTINGS, **doc}


async def notify(user_id: str, notification_type: str, title: str, body: str,
                 data: Optional[Dict[str, Any]] = None) -> None:
    """Insert a notification for a single user."""
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "body": body,
        "data": data or {},
        "read": False,
        "created_at": now_iso(),
    })


async def notify_all_admins(notification_type: str, title: str, body: str,
                            data: Optional[Dict[str, Any]] = None) -> None:
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(1000)
    for a in admins:
        await notify(a["id"], notification_type, title, body, data)


async def check_admin_anomalies(user_id: str, email: str, ip: str, success: bool) -> None:
    """Fan out `security_anomaly` notifications on:
      1. successful login from a never-before-seen IP for this admin
      2. ≥3 failed attempts for this email in the last 5 minutes
    """
    now = datetime.now(timezone.utc)
    if success:
        prior = await db.audit_log.find_one(
            {"actor_id": user_id, "action": "admin.auth.success",
             "meta.ip": ip, "created_at": {"$lt": now_iso()}},
            {"_id": 0, "id": 1},
        )
        first_ever = await db.audit_log.count_documents(
            {"actor_id": user_id, "action": "admin.auth.success"}
        )
        if not prior and first_ever > 1:
            await notify_all_admins(
                "security_anomaly",
                "New admin login IP detected",
                f"{email} signed in from {ip} — first time seen.",
                {"kind": "new_ip", "email": email, "ip": ip, "user_id": user_id},
            )
    else:
        since = (now - timedelta(minutes=5)).isoformat()
        fail_count = await db.audit_log.count_documents({
            "action": {"$in": ["admin.auth.failed", "admin.auth.2fa_failed"]},
            "meta.email": email,
            "created_at": {"$gte": since},
        })
        if fail_count >= 3 and fail_count % 3 == 0:
            await notify_all_admins(
                "security_anomaly",
                "Admin login brute-force detected",
                f"{fail_count} failed attempts for {email} in the last 5 minutes (last IP {ip}).",
                {"kind": "brute_force", "email": email, "ip": ip, "count": fail_count},
            )


def generate_recovery_codes(n: int = 10) -> List[str]:
    """Human-readable one-time codes like `XK3F-7P2M-9QRS` (no ambiguous chars)."""
    import secrets
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = []
    for _ in range(n):
        parts = [''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
        codes.append("-".join(parts))
    return codes


def hash_recovery_code(code: str) -> str:
    normalized = code.replace("-", "").replace(" ", "").upper()
    return bcrypt.hashpw(normalized.encode(), bcrypt.gensalt()).decode()


def verify_recovery_code(code: str, hashed_list: List[str]) -> int:
    """Return the matching index or -1."""
    normalized = code.replace("-", "").replace(" ", "").upper()
    for i, h in enumerate(hashed_list):
        try:
            if bcrypt.checkpw(normalized.encode(), h.encode()):
                return i
        except Exception:
            continue
    return -1
