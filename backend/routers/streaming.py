"""Streaming router — live streams, watch sessions, save/export, comments."""
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

import live_stream_service
from core.auth import get_current_user
from core.db import db
from core.helpers import get_settings, notify, now_iso
from core.models import (
    Comment, CommentCreate, ExportStream,
    LiveStream, LiveStreamCreate, User,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# -----------------------------------------------------------------------------
# LIVE STREAMS
# -----------------------------------------------------------------------------
@router.get("/streams", response_model=List[LiveStream])
async def get_streams(is_live: Optional[bool] = None):
    query = {}
    if is_live is not None:
        query['is_live'] = is_live
    return await db.live_streams.find(query, {"_id": 0}).sort("start_time", -1).to_list(1000)


@router.get("/streams/{stream_id}", response_model=LiveStream)
async def get_stream_by_id(stream_id: str):
    stream = await db.live_streams.find_one({"id": stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


@router.post("/streams", response_model=LiveStream)
async def create_stream(stream_data: LiveStreamCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ("streamer", "admin"):
        raise HTTPException(status_code=403, detail="Streamer access required")
    if current_user.subscription_status != "active" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Active streamer subscription required")
    stream_id = str(uuid.uuid4())

    try:
        provision = await live_stream_service.provision_stream(stream_id)
    except Exception as e:
        logger.exception("Live provisioning failed")
        raise HTTPException(status_code=502, detail=f"Live infra unavailable: {str(e)[:180]}")

    provided_video = stream_data.video_url or provision["playback_url"]

    stream_doc = {
        "id": stream_id,
        "streamer_id": current_user.id,
        "streamer_name": current_user.name,
        **stream_data.model_dump(),
        "video_url": provided_video,
        "playback_url": provision["playback_url"],
        "ingest_url": provision["ingest_url"],
        "stream_key": provision.get("stream_key"),
        "live_mode": provision.get("mode", "mock"),
        "is_live": True,
        "viewers_count": 0,
        "start_time": now_iso(),
        "end_time": None,
        "views": 0,
        "qualified_views": 0,
        "saved": False,
        "exports": [],
    }
    await db.live_streams.insert_one(stream_doc.copy())
    followers = await db.follows.find(
        {"streamer_id": current_user.id}, {"_id": 0, "follower_id": 1}
    ).to_list(10000)
    for f in followers:
        await notify(f["follower_id"], "stream_live",
                     f"{current_user.name} is live",
                     stream_data.title,
                     {"stream_id": stream_id, "streamer_id": current_user.id})
    return LiveStream(**stream_doc)


@router.post("/streams/{stream_id}/end")
async def end_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream['streamer_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.live_streams.update_one(
        {"id": stream_id},
        {"$set": {"is_live": False, "end_time": now_iso()}},
    )
    try:
        await live_stream_service.stop_stream(stream_id)
    except Exception as e:
        logger.warning(f"Live teardown warning for {stream_id}: {e}")

    settings = await get_settings()
    rate = settings["earnings_per_view"]
    qualified = stream.get('qualified_views', stream.get('views', 0))
    earnings = round(qualified * rate, 4)
    if earnings > 0:
        await db.earnings.insert_one({
            "id": str(uuid.uuid4()),
            "streamer_id": current_user.id,
            "amount": earnings,
            "source": "views",
            "description": f"Earnings from stream: {stream['title']} ({qualified} qualified views)",
            "created_at": now_iso(),
        })
    return {"message": "Stream ended", "earnings": earnings, "qualified_views": qualified}


@router.post("/streams/{stream_id}/join")
async def join_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    result = await db.live_streams.update_one(
        {"id": stream_id, "is_live": True},
        {"$inc": {"viewers_count": 1, "views": 1}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stream not found or not live")
    return {"message": "Joined stream"}


@router.post("/streams/{stream_id}/heartbeat")
async def stream_heartbeat(stream_id: str, current_user: User = Depends(get_current_user)):
    """Client heartbeat every 60s. At view_threshold_minutes, qualified_views += 1 per viewer."""
    settings = await get_settings()
    threshold = int(settings["view_threshold_minutes"])
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    key = {"stream_id": stream_id, "user_id": current_user.id}
    session = await db.watch_sessions.find_one(key)
    if not session:
        session = {**key, "minutes": 0, "qualified": False, "started_at": now_iso()}
        await db.watch_sessions.insert_one(session.copy())

    if session.get("qualified"):
        return {"minutes": session["minutes"], "qualified": True, "threshold": threshold}

    new_minutes = int(session["minutes"]) + 1
    update = {"minutes": new_minutes, "last_seen": now_iso()}
    qualified_now = False
    if new_minutes >= threshold and not session.get("qualified"):
        update["qualified"] = True
        update["qualified_at"] = now_iso()
        qualified_now = True

    await db.watch_sessions.update_one(key, {"$set": update})
    if qualified_now:
        await db.live_streams.update_one({"id": stream_id}, {"$inc": {"qualified_views": 1}})
    return {"minutes": new_minutes,
            "qualified": qualified_now or session.get("qualified", False),
            "threshold": threshold}


@router.post("/streams/{stream_id}/qualified-view")
async def qualified_view(stream_id: str, current_user: User = Depends(get_current_user)):
    """DEPRECATED: kept for backward compat. Prefer /heartbeat."""
    result = await db.live_streams.update_one(
        {"id": stream_id}, {"$inc": {"qualified_views": 1}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"message": "Qualified view recorded"}


@router.post("/streams/{stream_id}/save")
async def save_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream['streamer_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.live_streams.update_one({"id": stream_id}, {"$set": {"saved": True}})
    return {"message": "Stream saved"}


@router.post("/streams/{stream_id}/export")
async def export_stream(stream_id: str, body: ExportStream, current_user: User = Depends(get_current_user)):
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream['streamer_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    if not stream.get("saved"):
        raise HTTPException(status_code=400, detail="Save the stream before exporting")
    allowed = {"youtube", "twitch", "x", "custom"}
    if body.platform not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    mock = True
    target_url = body.target_url or f"https://{body.platform}.com/viewclip/{stream_id}"
    note = None
    uploaded = False
    try:
        import export_service as _oauth_svc
        if body.platform == "youtube":
            candidate = body.target_url or stream.get("recording_url") or stream.get("playback_url")
            video_file_url = candidate if candidate else None
            result = await _oauth_svc.publish_to_youtube(
                current_user.id,
                stream.get("title", "View/Clip stream"),
                stream.get("description", "") or "Exported from View/Clip.",
                ["viewclip", "live", "stream"],
                video_url=video_file_url,
            )
            mock = bool(result.get("mock"))
            uploaded = bool(result.get("uploaded"))
            target_url = result.get("url") or target_url
            note = result.get("reason") or result.get("note")
        elif body.platform == "twitch":
            result = await _oauth_svc.publish_to_twitch(
                current_user.id,
                stream.get("title", "View/Clip stream"),
                stream.get("description", "") or "Exported from View/Clip.",
            )
            mock = bool(result.get("mock"))
            target_url = result.get("url") or target_url
            note = result.get("reason") or result.get("note")
    except Exception as e:
        logger.warning("Real publish failed, falling back to mock: %s", e)

    export_record = {
        "platform": body.platform,
        "target_url": target_url,
        "mock": mock,
        "uploaded": uploaded,
        "note": note,
        "exported_at": now_iso(),
    }
    await db.live_streams.update_one(
        {"id": stream_id}, {"$push": {"exports": export_record}}
    )
    return {"message": "Stream exported", "export": export_record}


# -----------------------------------------------------------------------------
# COMMENTS
# -----------------------------------------------------------------------------
@router.post("/comments", response_model=Comment)
async def create_comment(comment_data: CommentCreate, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    comment_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "user_name": current_user.name,
        **comment_data.model_dump(),
        "created_at": now_iso(),
    }
    await db.comments.insert_one(comment_doc.copy())
    return Comment(**comment_doc)


@router.get("/comments/{stream_id}", response_model=List[Comment])
async def get_comments(stream_id: str):
    return await db.comments.find(
        {"stream_id": stream_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
