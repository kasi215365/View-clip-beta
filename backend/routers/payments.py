"""Payments router — Standalone Stripe Integration (Independent of Emergent)"""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import stripe_service
from core.auth import get_current_user
from core.constants import GIFT_TIERS_BY_ID
from core.db import db
from core.helpers import get_settings, notify, now_iso
from core.models import CheckoutGiftBundle, CheckoutSubscribe, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_placeholder')

# Bridge class to replace the missing platform response types
class MockCheckoutResponse:
    def __init__(self, session_id, url):
        self.session_id = session_id
        self.url = url

# -----------------------------------------------------------------------------
# CHECKOUT
# -----------------------------------------------------------------------------
@router.post("/payments/checkout/subscribe")
async def checkout_subscribe(body: CheckoutSubscribe, request: Request,
                             current_user: User = Depends(get_current_user)):
    settings = await get_settings()
    if body.type == "viewer":
        amount = float(settings["viewer_sub_price"])
    elif body.type == "streamer":
        amount = float(settings["streamer_sub_price"])
    else:
        raise HTTPException(status_code=400, detail="Invalid subscription type")

    origin = body.origin_url.rstrip('/')
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/profile"

    if stripe_service.real_stripe_enabled():
        try:
            price_id = await stripe_service.ensure_subscription_price(body.type, amount)
            session = stripe_service.create_subscription_checkout(
                price_id=price_id,
                customer_email=current_user.email,
                user_id=current_user.id,
                sub_type=body.type,
                success_url=success_url,
                cancel_url=cancel_url,
            )
            metadata = {"sub_type": body.type, "recurring": True, "price_id": price_id}
            url = session["url"]
            session_id = session["session_id"]
        except Exception as e:
            logger.exception("Real Stripe subscription failed, falling back")
            raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)[:180]}")
    else:
        # Standalone Bypass: Replaced platform tool with local logic
        session_id = f"mock_{uuid.uuid4()}"
        # We replace the placeholder in the success_url manually for the mock flow
        url = success_url.replace("{CHECKOUT_SESSION_ID}", session_id)
        metadata = {"sub_type": body.type, "recurring": False}

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": current_user.id,
        "email": current_user.email,
        "amount": amount,
        "currency": "usd",
        "purpose": "subscription",
        "metadata": metadata,
        "payment_status": "pending",
        "status": "initiated",
        "processed": False,
        "created_at": now_iso(),
    })
    return {"url": url, "session_id": session_id, "recurring": metadata.get("recurring", False)}


@router.post("/payments/subscription/cancel")
async def cancel_subscription_endpoint(current_user: User = Depends(get_current_user)):
    sub = await db.subscriptions.find_one(
        {"user_id": current_user.id, "status": "active",
         "stripe_subscription_id": {"$exists": True}},
        {"_id": 0},
    )
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription to cancel")
    try:
        stripe_service.cancel_subscription(sub["stripe_subscription_id"], at_period_end=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)[:180]}")
    await db.subscriptions.update_one(
        {"id": sub["id"]},
        {"$set": {"cancel_at_period_end": True, "cancelled_at": now_iso()}},
    )
    return {"message": "Subscription will cancel at period end", "expires_at": sub.get("expires_at")}


@router.post("/payments/checkout/gift-bundle")
async def checkout_gift_bundle(body: CheckoutGiftBundle, request: Request,
                               current_user: User = Depends(get_current_user)):
    tier = GIFT_TIERS_BY_ID.get(body.tier_id)
    if not tier:
        raise HTTPException(status_code=400, detail="Invalid gift tier")

    amount = float(tier["price"])
    origin = body.origin_url.rstrip('/')
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/profile"

    # Standalone Bypass for gift bundles
    session_id = f"mock_{uuid.uuid4()}"
    url = success_url.replace("{CHECKOUT_SESSION_ID}", session_id)
    
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": current_user.id,
        "email": current_user.email,
        "amount": amount,
        "currency": "usd",
        "purpose": "gift_bundle",
        "metadata": {"tier_id": tier["id"], "qty": tier["qty"]},
        "payment_status": "pending",
        "status": "initiated",
        "processed": False,
        "created_at": now_iso(),
    })
    return {"url": url, "session_id": session_id}


@router.get("/payments/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request,
                              current_user: User = Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx["user_id"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    # If it's a mock transaction, we simulate a 'paid' status for your testing
    if session_id.startswith("mock_"):
        payment_status = "paid"
        status = "completed"
    else:
        # This will only run if you have real Stripe configured
        try:
            stripe_data = stripe_service.retrieve_checkout_session(session_id)
            payment_status = stripe_data.get("payment_status", "unpaid")
            status = stripe_data.get("status", "open")
        except:
            payment_status = "unpaid"
            status = "open"

    if not tx.get("processed") and payment_status == "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id, "processed": {"$ne": True}},
            {"$set": {"status": status,
                      "payment_status": payment_status,
                      "processed": True, "completed_at": now_iso()}},
        )
        await fulfill_payment(tx)
    
    return {
        "status": status,
        "payment_status": payment_status,
        "amount_total": tx.get("amount"),
        "currency": "usd",
        "purpose": tx.get("purpose"),
        "metadata": tx.get("metadata"),
    }


async def fulfill_payment(tx: Dict[str, Any]):
    """Idempotent fulfilment based on tx['purpose']."""
    purpose = tx.get("purpose")
    user_id = tx["user_id"]
    if purpose == "subscription":
        sub_type = tx["metadata"]["sub_type"]
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        sub_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": sub_type,
            "amount": tx["amount"],
            "status": "active",
            "created_at": now_iso(),
            "expires_at": expires,
            "session_id": tx["session_id"],
            "stripe_subscription_id": tx.get("stripe_subscription_id"),
            "stripe_customer_id": tx.get("stripe_customer_id"),
            "recurring": True,
        }
        await db.subscriptions.insert_one(sub_doc.copy())
        update = {"subscription_status": "active", "subscription_expires": expires}
        if sub_type == "streamer":
            update["role"] = "streamer"
        await db.users.update_one({"id": user_id}, {"$set": update})
    elif purpose == "gift_bundle":
        tier_id = tx["metadata"]["tier_id"]
        qty = int(tx["metadata"]["qty"])
        user = await db.users.find_one({"id": user_id})
        wallet = (user or {}).get("gift_wallet", {})
        wallet[tier_id] = int(wallet.get(tier_id, 0)) + qty
        await db.users.update_one({"id": user_id}, {"$set": {"gift_wallet": wallet}})


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Unified webhook for official Stripe events."""
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")

    native_event = stripe_service.verify_webhook(body, sig)
    if not native_event:
        return {"received": True, "status": "no_event"}

    etype = native_event.get("type")
    obj = native_event["data"]["object"]

    if etype == "checkout.session.completed":
        session_id = obj["id"]
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")
        tx = await db.payment_transactions.find_one({"session_id": session_id})
        if tx and not tx.get("processed"):
            await db.payment_transactions.update_one(
                {"session_id": session_id, "processed": {"$ne": True}},
                {"$set": {"processed": True, "payment_status": "paid",
                          "status": "completed",
                          "stripe_subscription_id": subscription_id,
                          "stripe_customer_id": customer_id,
                          "completed_at": now_iso()}},
            )
            await fulfill_payment({**tx, "stripe_subscription_id": subscription_id,
                                   "stripe_customer_id": customer_id})

    return {"received": True, "handled": etype}

@router.get("/subscriptions/status")
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    subscription = await db.subscriptions.find_one(
        {"user_id": current_user.id, "status": "active"}, {"_id": 0}
    )
    return {"has_subscription": subscription is not None, "subscription": subscription}

@router.post("/streamers/connect/onboard")
async def connect_onboard(current_user: User = Depends(get_current_user)):
    if current_user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer access required")

    if not stripe_service.real_stripe_enabled():
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {"connect_account_status": "active", "connect_onboarded_at": now_iso()}},
        )
        return {
            "message": "Connect onboarding mock complete",
            "onboarding_url": "https://connect.stripe.com/express/onboarding/mock",
            "status": "active",
            "mock": True,
        }

    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    try:
        account_id = user_doc.get("connect_account_id")
        if not account_id:
            account_id = stripe_service.create_connect_account(email=current_user.email)
            await db.users.update_one(
                {"id": current_user.id},
                {"$set": {"connect_account_id": account_id,
                          "connect_account_status": "pending"}},
            )
        base = os.environ.get("PUBLIC_APP_URL", "").rstrip("/") or ""
        refresh_url = f"{base}/profile"
        return_url = f"{base}/profile?connect=done"
        link = stripe_service.create_onboarding_link(account_id, refresh_url, return_url)
        return {"onboarding_url": link, "account_id": account_id, "status": "pending"}
    except Exception as e:
        logger.exception("Connect onboard failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)[:180]}")

@router.get("/streamers/connect/status")
async def connect_status(current_user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one(
        {"id": current_user.id}, {"_id": 0, "connect_account_id": 1}
    )
    account_id = (user_doc or {}).get("connect_account_id")
    if not account_id:
        return {"configured": False}
    try:
        info = stripe_service.retrieve_account(account_id)
    except Exception as e:
        return {"configured": True, "error": str(e)[:180]}
    status = "active" if info.get("charges_enabled") and info.get("payouts_enabled") else "pending"
    await db.users.update_one(
        {"id": current_user.id}, {"$set": {"connect_account_status": status}}
    )
    return {"configured": True, "status": status, **info}
