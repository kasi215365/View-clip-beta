"""Content router — VOD catalog + promos."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user, require_admin
from core.db import db
from core.helpers import now_iso
from core.models import Content, ContentCreate, PromoCreate, User

router = APIRouter(prefix="/api")


# --- VOD catalog ---------------------------------------------------------
@router.get("/content", response_model=List[Content])
async def get_content(type: Optional[str] = None):
    query = {"is_promo": {"$ne": True}}
    if type:
        query['type'] = type
    return await db.content.find(query, {"_id": 0}).to_list(1000)


@router.get("/content/{content_id}", response_model=Content)
async def get_content_by_id(content_id: str):
    content = await db.content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/content", response_model=Content)
async def create_content(content_data: ContentCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    content_id = str(uuid.uuid4())
    content_doc = {"id": content_id, **content_data.model_dump(), "views": 0, "created_at": now_iso()}
    await db.content.insert_one(content_doc.copy())
    return Content(**content_doc)


@router.post("/content/{content_id}/view")
async def increment_content_view(content_id: str, current_user: User = Depends(get_current_user)):
    result = await db.content.update_one({"id": content_id}, {"$inc": {"views": 1}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"message": "View recorded"}


# --- Self-promotion engine -----------------------------------------------
@router.get("/promos", response_model=List[Content])
async def list_promos():
    return await db.content.find({"is_promo": True}, {"_id": 0}).to_list(100)


@router.post("/promos", response_model=Content)
async def create_promo(promo: PromoCreate, _admin: User = Depends(require_admin)):
    promo_doc = {
        "id": str(uuid.uuid4()),
        "title": promo.title,
        "description": promo.description,
        "thumbnail_url": promo.thumbnail_url,
        "video_url": promo.video_url,
        "type": "promo",
        "duration": 30,
        "is_promo": True,
        "views": 0,
        "created_at": now_iso(),
    }
    await db.content.insert_one(promo_doc.copy())
    return Content(**promo_doc)


@router.delete("/promos/{promo_id}")
async def delete_promo(promo_id: str, _admin: User = Depends(require_admin)):
    res = await db.content.delete_one({"id": promo_id, "is_promo": True})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promo not found")
    return {"message": "deleted"}
