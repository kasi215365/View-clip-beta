"""Social / discovery endpoints — follows, referrals, search, trending."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from core.helpers import generate_referral_code, notify, now_iso
from core.models import User

router = APIRouter(prefix="/api")


# -----------------------------------------------------------------------------
# REFERRALS
# -----------------------------------------------------------------------------
@router.get("/referrals/my")
async def my_referrals(current_user: User = Depends(get_current_user)):
    user = await db.users.find_one(
        {"id": current_user.id},
        {"_id": 0, "referral_code": 1, "referral_earnings": 1},
    )
    code = (user or {}).get("referral_code")
    if not code:
        code = generate_referral_code(current_user.name, current_user.id)
        await db.users.update_one(
            {"id": current_user.id}, {"$set": {"referral_code": code}}
        )
    referred_users = await db.users.count_documents({"referred_by": current_user.id})
    events = await db.referral_events.find(
        {"referrer_id": current_user.id}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {
        "code": code,
        "referred_count": referred_users,
        "earnings": round(float((user or {}).get("referral_earnings", 0.0)), 4),
        "events": events,
    }


@router.get("/referrals/leaderboard")
async def referral_leaderboard():
    """Top 50 referrers by referral_earnings — public."""
    pipeline = [
        {"$match": {"referral_earnings": {"$gt": 0}}},
        {"$sort": {"referral_earnings": -1}},
        {"$limit": 50},
        {"$project": {"_id": 0, "name": 1, "referral_code": 1,
                      "referral_earnings": 1, "role": 1}},
    ]
    rows = await db.users.aggregate(pipeline).to_list(50)
    enriched = []
    for i, r in enumerate(rows):
        owner = await db.users.find_one(
            {"referral_code": r["referral_code"]}, {"_id": 0, "id": 1}
        )
        count = await db.users.count_documents({"referred_by": (owner or {}).get("id")})
        enriched.append({
            **r, "rank": i + 1,
            "referred_count": count,
            "earnings": round(r["referral_earnings"], 2),
        })
    return {"leaderboard": enriched}


@router.get("/referrals/validate/{code}")
async def validate_referral_code(code: str):
    user = await db.users.find_one({"referral_code": code.upper()}, {"_id": 0, "name": 1})
    if not user:
        return {"valid": False}
    return {"valid": True, "referrer_name": user["name"]}


# -----------------------------------------------------------------------------
# FOLLOW / UNFOLLOW STREAMERS
# -----------------------------------------------------------------------------
@router.post("/streamers/{streamer_id}/follow")
async def follow_streamer(streamer_id: str, current_user: User = Depends(get_current_user)):
    if streamer_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    streamer = await db.users.find_one({"id": streamer_id}, {"_id": 0, "name": 1, "role": 1})
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    existing = await db.follows.find_one(
        {"follower_id": current_user.id, "streamer_id": streamer_id}
    )
    if existing:
        return {"message": "Already following", "following": True}

    await db.follows.insert_one({
        "id": str(uuid.uuid4()),
        "follower_id": current_user.id,
        "streamer_id": streamer_id,
        "created_at": now_iso(),
    })
    await notify(streamer_id, "new_follower",
                 "New follower!",
                 f"{current_user.name} started following you.",
                 {"follower_id": current_user.id})
    return {"message": "Followed", "following": True}


@router.post("/streamers/{streamer_id}/unfollow")
async def unfollow_streamer(streamer_id: str, current_user: User = Depends(get_current_user)):
    res = await db.follows.delete_one(
        {"follower_id": current_user.id, "streamer_id": streamer_id}
    )
    return {"message": "Unfollowed" if res.deleted_count else "Was not following",
            "following": False}


@router.get("/streamers/{streamer_id}/follow-status")
async def follow_status(streamer_id: str, current_user: User = Depends(get_current_user)):
    exists = await db.follows.find_one(
        {"follower_id": current_user.id, "streamer_id": streamer_id}
    )
    followers = await db.follows.count_documents({"streamer_id": streamer_id})
    return {"following": exists is not None, "followers_count": followers}


@router.get("/users/me/follows")
async def my_follows(current_user: User = Depends(get_current_user)):
    rows = await db.follows.find(
        {"follower_id": current_user.id}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    out = []
    for r in rows:
        s = await db.users.find_one(
            {"id": r["streamer_id"]}, {"_id": 0, "id": 1, "name": 1, "role": 1}
        )
        if s:
            live = await db.live_streams.find_one(
                {"streamer_id": r["streamer_id"], "is_live": True}, {"_id": 0}
            )
            out.append({**s, "followed_at": r["created_at"],
                        "live_stream_id": (live or {}).get("id")})
    return {"follows": out}


# -----------------------------------------------------------------------------
# SEARCH + TRENDING
# -----------------------------------------------------------------------------
@router.get("/search")
async def search(q: str):
    """Unified search across content, streams and streamers."""
    q_str = (q or "").strip()
    if len(q_str) < 2:
        return {"content": [], "streams": [], "streamers": [], "query": q_str}
    regex = {"$regex": q_str, "$options": "i"}
    content = await db.content.find(
        {"$or": [{"title": regex}, {"description": regex}], "is_promo": {"$ne": True}},
        {"_id": 0},
    ).limit(20).to_list(20)
    streams = await db.live_streams.find(
        {"$or": [{"title": regex}, {"description": regex}, {"streamer_name": regex}]},
        {"_id": 0},
    ).sort("start_time", -1).limit(20).to_list(20)
    streamers = await db.users.find(
        {"role": {"$in": ["streamer", "admin"]}, "name": regex},
        {"_id": 0, "password_hash": 0},
    ).limit(20).to_list(20)
    return {"content": content, "streams": streams,
            "streamers": streamers, "query": q_str}


@router.get("/trending")
async def trending():
    """Top VOD content and live streams ranked by views."""
    content = await db.content.find(
        {"is_promo": {"$ne": True}}, {"_id": 0}
    ).sort("views", -1).limit(12).to_list(12)
    streams = await db.live_streams.find(
        {"is_live": True}, {"_id": 0}
    ).sort("viewers_count", -1).limit(12).to_list(12)
    return {"content": content, "live_streams": streams}
