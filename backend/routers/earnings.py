"""Earnings + streamer analytics router."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.db import db
from core.models import User

router = APIRouter(prefix="/api")


@router.get("/earnings")
async def get_earnings(current_user: User = Depends(get_current_user)):
    return await db.earnings.find(
        {"streamer_id": current_user.id}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)


@router.get("/earnings/total")
async def get_total_earnings(current_user: User = Depends(get_current_user)):
    pipeline = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    result = await db.earnings.aggregate(pipeline).to_list(1)
    total = result[0]['total'] if result else 0
    return {"total_earnings": round(total, 4)}


@router.get("/streamers/me/analytics")
async def my_analytics(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("streamer", "admin"):
        raise HTTPException(status_code=403, detail="Streamer access required")

    by_source_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": "$source", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    by_source = {r["_id"]: {"total": round(r["total"], 4), "count": r["count"]}
                 for r in await db.earnings.aggregate(by_source_pipe).to_list(10)}

    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    ts_pipe = [
        {"$match": {"streamer_id": current_user.id, "created_at": {"$gte": since}}},
        {"$project": {"day": {"$substr": ["$created_at", 0, 10]}, "amount": 1}},
        {"$group": {"_id": "$day", "total": {"$sum": "$amount"}}},
        {"$sort": {"_id": 1}},
    ]
    series = [{"date": r["_id"], "amount": round(r["total"], 4)}
              for r in await db.earnings.aggregate(ts_pipe).to_list(40)]

    gifters_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": "$sender_id", "sender_name": {"$first": "$sender_name"},
                    "total_value": {"$sum": "$value"}, "count": {"$sum": "$quantity"}}},
        {"$sort": {"total_value": -1}},
        {"$limit": 10},
    ]
    top_gifters = [{"sender_id": r["_id"], "name": r["sender_name"],
                    "total_value": round(r["total_value"], 3), "count": r["count"]}
                   for r in await db.gifts.aggregate(gifters_pipe).to_list(10)]

    tiers_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": "$tier_id", "emoji": {"$first": "$tier_emoji"},
                    "name": {"$first": "$tier_name"}, "count": {"$sum": "$quantity"},
                    "value": {"$sum": "$value"}}},
        {"$sort": {"value": -1}},
    ]
    tiers = [{"tier_id": r["_id"], "emoji": r["emoji"], "name": r["name"],
              "count": r["count"], "value": round(r["value"], 3)}
             for r in await db.gifts.aggregate(tiers_pipe).to_list(10)]

    total_streams = await db.live_streams.count_documents({"streamer_id": current_user.id})
    live_now = await db.live_streams.count_documents({"streamer_id": current_user.id, "is_live": True})
    views_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": None, "views": {"$sum": "$views"},
                    "qualified": {"$sum": "$qualified_views"}}},
    ]
    v_rows = await db.live_streams.aggregate(views_pipe).to_list(1)
    views_total = v_rows[0] if v_rows else {"views": 0, "qualified": 0}
    followers = await db.follows.count_documents({"streamer_id": current_user.id})

    return {
        "by_source": by_source,
        "time_series": series,
        "top_gifters": top_gifters,
        "gift_tiers": tiers,
        "streams": {"total": total_streams, "live_now": live_now,
                    "views": int(views_total.get("views", 0)),
                    "qualified_views": int(views_total.get("qualified", 0))},
        "followers": followers,
    }
