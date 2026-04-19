"""Gifts router — tier catalog + wallet + send."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.constants import GIFT_TIERS, GIFT_TIERS_BY_ID
from core.db import db
from core.helpers import get_settings, notify, now_iso
from core.models import GiftSend, User

router = APIRouter(prefix="/api")


@router.get("/gifts/tiers")
async def list_gift_tiers():
    return {"tiers": GIFT_TIERS}


@router.get("/gifts/wallet")
async def get_wallet(current_user: User = Depends(get_current_user)):
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "gift_wallet": 1})
    return {"wallet": (user or {}).get("gift_wallet", {})}


@router.post("/gifts/send")
async def send_gift(body: GiftSend, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    tier = GIFT_TIERS_BY_ID.get(body.tier_id)
    if not tier:
        raise HTTPException(status_code=400, detail="Invalid gift tier")
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")
    if not body.stream_id and not body.recipient_id:
        raise HTTPException(status_code=400, detail="Provide stream_id or recipient_id")

    stream = None
    if body.stream_id:
        stream = await db.live_streams.find_one({"id": body.stream_id})
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")
    recipient_id = body.recipient_id or (stream and stream["streamer_id"])
    if not recipient_id or recipient_id == current_user.id:
        raise HTTPException(status_code=400, detail="Invalid recipient")
    recipient = await db.users.find_one({"id": recipient_id}, {"_id": 0, "id": 1, "name": 1})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Decrement sender wallet
    user = await db.users.find_one({"id": current_user.id})
    wallet = (user or {}).get("gift_wallet", {})
    balance = int(wallet.get(body.tier_id, 0))
    if balance < body.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient {tier['emoji']} {tier['name']} units. Purchase a bundle first.",
        )
    wallet[body.tier_id] = balance - body.quantity
    await db.users.update_one({"id": current_user.id}, {"$set": {"gift_wallet": wallet}})

    settings = await get_settings()
    base_rate = settings["gift_base_rate"]
    per_unit = max(tier["value_per_unit"], base_rate)
    earnings = round(per_unit * body.quantity, 4)

    gift_doc = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "streamer_id": recipient_id,   # back-compat alias
        "recipient_id": recipient_id,
        "recipient_name": recipient["name"],
        "stream_id": body.stream_id,
        "tier_id": body.tier_id,
        "tier_emoji": tier["emoji"],
        "tier_name": tier["name"],
        "quantity": body.quantity,
        "value": earnings,
        "direct": body.stream_id is None,
        "created_at": now_iso(),
    }
    await db.gifts.insert_one(gift_doc.copy())
    await db.earnings.insert_one({
        "id": str(uuid.uuid4()),
        "streamer_id": recipient_id,
        "user_id": recipient_id,
        "amount": earnings,
        "source": "gifts",
        "description": f"{body.quantity}x {tier['emoji']} {tier['name']} from {current_user.name}"
                       + (f" (on stream: {stream['title']})" if stream else " (direct gift)"),
        "created_at": now_iso(),
    })
    await notify(
        recipient_id, "gift_received",
        f"{tier['emoji']} Gift from {current_user.name}",
        f"{body.quantity}x {tier['name']} (+${earnings:.3f})",
        {"stream_id": body.stream_id, "amount": earnings,
         "sender_id": current_user.id, "sender_name": current_user.name},
    )
    return {"message": "Gift sent", "gift": gift_doc,
            "recipient_earned": earnings, "streamer_earned": earnings}
