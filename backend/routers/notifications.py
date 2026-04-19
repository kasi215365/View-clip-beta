"""User notifications — list, mark read, mark all read."""
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from core.models import User

router = APIRouter(prefix="/api")


@router.get("/notifications")
async def list_notifications(current_user: User = Depends(get_current_user)):
    rows = await db.notifications.find(
        {"user_id": current_user.id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    unread = sum(1 for r in rows if not r.get("read"))
    return {"notifications": rows, "unread_count": unread}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    res = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "marked read"}


@router.post("/notifications/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    res = await db.notifications.update_many(
        {"user_id": current_user.id, "read": False},
        {"$set": {"read": True}},
    )
    return {"message": "all marked read", "count": res.modified_count}
