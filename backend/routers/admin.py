# from live_stream_service import stop_stream, PROJECT_ID, LOCATION
# from google.cloud.video import live_stream_v1

@router.post("/kill-all-streams")
async def kill_all_streams():
    """Emergency shutdown for all active GCP infrastructure."""
    try:
        from google.cloud.video import live_stream_v1
        from live_stream_service import stop_stream, PROJECT_ID, LOCATION

        client = live_stream_v1.LivestreamServiceClient()
        parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
        
        channels = client.list_channels(parent=parent)
        count = 0
        for channel in channels:
            # Extract ID from 'projects/.../locations/.../channels/ID'
            c_id = channel.name.split('/')[-1]
            stream_id = c_id.replace("vc-ch-", "")
            await stop_stream(stream_id)
            count += 1
            
        return {"status": "success", "terminated": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
"""Admin command center — stats, users, settings, payouts, system/health,
deploy-update, rotate-keys, system events, audit log, streaming-provider switch."""
import logging
import os
import time
import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

import live_stream_service
import stripe_service
from core import crypto as _crypto
from core import firewall as fw
from core.auth import require_admin
from core.crypto import vault_key_configured
from core.db import db, db_identity, db_streaming, db_vault
from core.helpers import get_settings, notify, now_iso
from core.models import AdminSettingsUpdate, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

APP_START_TIME = time.time()


# -----------------------------------------------------------------------------
# ADMIN STATS / USERS / SETTINGS
# -----------------------------------------------------------------------------
@router.get("/admin/stats")
async def admin_stats(_admin: User = Depends(require_admin)):
    users_total = await db.users.count_documents({})
    viewers = await db.users.count_documents({"role": "viewer"})
    streamers = await db.users.count_documents({"role": "streamer"})
    active_subs = await db.users.count_documents({"subscription_status": "active"})
    streams_total = await db.live_streams.count_documents({})
    streams_live = await db.live_streams.count_documents({"is_live": True})
    content_total = await db.content.count_documents({"is_promo": {"$ne": True}})
    promos_total = await db.content.count_documents({"is_promo": True})

    total_revenue_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    rev = await db.payment_transactions.aggregate([
        {"$match": {"processed": True}},
        *total_revenue_pipeline,
    ]).to_list(1)
    total_revenue = rev[0]["total"] if rev else 0.0

    payouts = await db.earnings.aggregate(total_revenue_pipeline).to_list(1)
    total_payouts = payouts[0]["total"] if payouts else 0.0

    gifts_count = await db.gifts.count_documents({})
    return {
        "users": {"total": users_total, "viewers": viewers, "streamers": streamers,
                  "active_subscriptions": active_subs},
        "streams": {"total": streams_total, "live_now": streams_live},
        "content": {"total": content_total, "promos": promos_total},
        "gifts": {"total_sent": gifts_count},
        "financials": {
            "total_revenue": round(total_revenue, 2),
            "total_payouts_owed": round(total_payouts, 4),
            "net": round(total_revenue - total_payouts, 2),
        },
    }


@router.get("/admin/users")
async def admin_users(_admin: User = Depends(require_admin)):
    users = await db.users.find(
        {}, {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).to_list(1000)
    return {"users": users}


@router.get("/admin/settings")
async def admin_get_settings(_admin: User = Depends(require_admin)):
    return await get_settings()


@router.post("/admin/settings")
async def admin_update_settings(body: AdminSettingsUpdate, _admin: User = Depends(require_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")
    updates["updated_at"] = now_iso()
    await db.settings.update_one({"id": "global"}, {"$set": updates}, upsert=True)
    return await get_settings()


# -----------------------------------------------------------------------------
# PAYOUTS
# -----------------------------------------------------------------------------
@router.post("/admin/payouts/trigger")
async def admin_trigger_payouts(_admin: User = Depends(require_admin)):
    pipeline = [
        {"$match": {"paid_out": {"$ne": True}}},
        {"$group": {"_id": "$streamer_id", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    by_streamer = await db.earnings.aggregate(pipeline).to_list(10000)
    real_mode = stripe_service.real_stripe_enabled()
    paid = skipped = errors = 0
    total_paid = 0.0
    for row in by_streamer:
        streamer_id = row["_id"]
        amount = round(row["total"], 4)
        if amount <= 0:
            continue
        user_doc = await db.users.find_one(
            {"id": streamer_id},
            {"_id": 0, "connect_account_id": 1, "connect_account_status": 1, "name": 1},
        )
        account_id = (user_doc or {}).get("connect_account_id")
        if real_mode:
            if not account_id or (user_doc or {}).get("connect_account_status") != "active":
                skipped += 1
                continue
            try:
                tr = stripe_service.transfer_to_connect(
                    account_id=account_id,
                    amount_usd=amount,
                    description=f"View/Clip payout for {user_doc.get('name')}",
                )
                transfer_id = tr["id"]
                status = "completed"
            except Exception as e:
                errors += 1
                logger.error(f"Transfer failed for {streamer_id}: {e}")
                continue
        else:
            transfer_id = f"mock_tr_{uuid.uuid4().hex[:12]}"
            status = "completed_mock"

        await db.earnings.update_many(
            {"streamer_id": streamer_id, "paid_out": {"$ne": True}},
            {"$set": {"paid_out": True, "paid_out_at": now_iso(),
                      "stripe_transfer_id": transfer_id}},
        )
        await db.payouts.insert_one({
            "id": str(uuid.uuid4()),
            "streamer_id": streamer_id,
            "amount": amount,
            "earnings_count": row["count"],
            "stripe_transfer_id": transfer_id,
            "status": status,
            "processed_at": now_iso(),
        })
        await notify(streamer_id, "payout", "Payout sent",
                     f"${amount:.2f} transferred.",
                     {"amount": amount, "transfer_id": transfer_id})
        paid += 1
        total_paid += amount

    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": _admin.id,
        "action": "payouts.trigger",
        "meta": {"paid": paid, "skipped": skipped, "errors": errors,
                 "total_paid": round(total_paid, 2), "real_mode": real_mode},
        "created_at": now_iso(),
    })
    return {"message": "Payouts processed", "streamers_paid": paid,
            "skipped_no_connect": skipped, "errors": errors,
            "total_paid": round(total_paid, 2), "real_mode": real_mode}


@router.get("/admin/payouts")
async def admin_list_payouts(_admin: User = Depends(require_admin)):
    payouts = await db.payouts.find({}, {"_id": 0}).sort("processed_at", -1).to_list(1000)
    return {"payouts": payouts}


# -----------------------------------------------------------------------------
# SYSTEM CONTROL CENTER
# -----------------------------------------------------------------------------
@router.get("/admin/system/health")
async def admin_system_health(_admin: User = Depends(require_admin)):
    async def ping(dbh, name):
        t0 = time.time()
        try:
            await dbh.command("ping")
            return {"layer": name, "status": "ok",
                    "latency_ms": round((time.time() - t0) * 1000, 2)}
        except Exception as e:
            return {"layer": name, "status": "error", "error": str(e)[:120]}
    layers = [
        await ping(db_identity, "identity"),
        await ping(db_streaming, "streaming"),
        await ping(db_vault, "vault"),
    ]
    uptime = int(time.time() - APP_START_TIME)
    return {
        "version": os.environ.get("APP_VERSION", "1.4.0"),
        "uptime_seconds": uptime,
        "uptime_human": f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s",
        "layers": layers,
        "requests": {"total": fw._REQUEST_COUNTER["total"],
                     "top_paths": sorted(fw._REQUEST_COUNTER["by_path"].items(),
                                         key=lambda x: -x[1])[:10]},
        "firewall": {
            "rate_limit_per_min": int(os.environ.get("FIREWALL_RATE_LIMIT_PER_MIN", "300")),
            "blocked_requests": fw._REQUEST_COUNTER.get("blocked", 0),
            "admin_ip_allowlist_enabled": bool(fw._ADMIN_ALLOWLIST_NETS),
            "admin_ip_allowlist_count": len(fw._ADMIN_ALLOWLIST_NETS),
        },
        "encryption": {"algorithm": "Fernet (AES-128-CBC + HMAC-SHA256)",
                       "vault_key_configured": vault_key_configured()},
                    "integrations": {
            "stripe_mode": "real" if stripe_service.real_stripe_enabled() else "mock (emergentintegrations)",
            "livestream_mode": "gcp-livestream" if live_stream_service.is_live_enabled() else "mock",
            "gcp_burn_stats": await live_stream_service.active_channels_cost(),
        },
    } # <--- THIS BRACKET WAS MISSING, CLOSING THE HEALTH CHECK

@router.post("/admin/system/emergency-kill-streams")
async def admin_emergency_kill_streams(_admin: User = Depends(require_admin)):
    """The 'Big Red Button' — terminates all active GCP channels immediately."""
    try:
        from google.cloud.video import live_stream_v1
        from live_stream_service import PROJECT_ID, LOCATION, stop_stream

        client_gcp = live_stream_v1.LivestreamServiceClient()
        parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
        
        channels = client_gcp.list_channels(parent=parent)
        terminated_count = 0
        
        for channel in channels:
            c_id = channel.name.split('/')[-1]
            stream_id = c_id.replace("vc-ch-", "")
            await live_stream_service.stop_stream(stream_id)
            terminated_count += 1

        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "actor_id": _admin.id,
            "action": "system.emergency_kill",
            "meta": {"terminated_count": terminated_count, "timestamp": now_iso()},
            "created_at": now_iso(),
        })

        logger.warning(f"EMERGENCY KILL executed by admin {_admin.id}. {terminated_count} streams stopped.")
        
        return {
            "message": "Emergency shutdown complete",
            "terminated_count": terminated_count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Emergency kill failed: {e}")
        raise HTTPException(status_code=500, detail=f"Shutdown failed: {str(e)}")

@router.post("/admin/system/reload-settings")
async def admin_reload_settings(_admin: User = Depends(require_admin)):
    settings = await get_settings()
    await db.system_events.insert_one({
        "id": str(uuid.uuid4()), "type": "settings.reload",
        "actor": _admin.id, "created_at": now_iso(),
    })
    return {"message": "Settings reloaded", "settings": settings}


@router.post("/admin/system/deploy-update")
async def admin_deploy_update(_admin: User = Depends(require_admin)):
    version = os.environ.get("APP_VERSION", "1.4.0")
    event = {
        "id": str(uuid.uuid4()), "type": "deploy.update", "version": version,
        "actor": _admin.id, "created_at": now_iso(), "status": "completed",
    }
    await db.system_events.insert_one(event.copy())
    return {"message": f"Update v{version} applied", "event": event}

@router.post("/admin/system/rotate-keys")
async def admin_rotate_keys(_admin: User = Depends(require_admin)):
    """Rotate the Fernet vault key. Re-encrypts banking_info + users.totp_secret
    with the new cipher, then swaps the active cipher in-process."""
    from cryptography.fernet import Fernet as _F

    new_key = _F.generate_key().decode()
    old_cipher = _crypto.current_cipher()
    new_cipher = _F(new_key.encode())

    rotated = failed = 0
    async for row in db.banking_info.find({}):
        patch = {}
        for fld in ("account_number_enc", "routing_number_enc"):
            enc = row.get(fld)
            if not enc:
                continue
            try:
                plain = old_cipher.decrypt(enc.encode()).decode()
                patch[fld] = new_cipher.encrypt(plain.encode()).decode()
            except Exception:
                failed += 1
        if patch:
            patch["key_rotated_at"] = now_iso()
            await db.banking_info.update_one({"_id": row["_id"]}, {"$set": patch})
            rotated += 1

    totp_rotated = totp_failed = 0
    async for u in db.users.find({"totp_secret": {"$exists": True, "$ne": None}}):
        enc = u.get("totp_secret")
        if not enc:
            continue
        try:
            plain = old_cipher.decrypt(enc.encode()).decode()
            new_enc = new_cipher.encrypt(plain.encode()).decode()
            await db.users.update_one(
                {"_id": u["_id"]},
                {"$set": {"totp_secret": new_enc, "totp_key_rotated_at": now_iso()}},
            )
            totp_rotated += 1
        except Exception:
            totp_failed += 1

    _crypto.replace_cipher(new_key)

    event = {
        "id": str(uuid.uuid4()), "type": "keys.rotate", "actor": _admin.id,
        "rotated_records": rotated, "failed_records": failed,
        "totp_rotated": totp_rotated, "totp_failed": totp_failed,
        "created_at": now_iso(),
    }
    await db.system_events.insert_one(event.copy())
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": _admin.id,
        "action": "keys.rotate",
        "meta": {"rotated": rotated, "failed": failed,
                 "totp_rotated": totp_rotated, "totp_failed": totp_failed},
        "created_at": now_iso(),
    })
    logger.info("Vault key rotated — banking:%d/%d | totp:%d/%d",
                rotated, failed, totp_rotated, totp_failed)
    return {
        "message": (f"Key rotated. Banking: {rotated} re-encrypted ({failed} failed). "
                    f"TOTP secrets: {totp_rotated} re-encrypted ({totp_failed} failed)."),
        "rotated": rotated, "failed": failed,
        "totp_rotated": totp_rotated, "totp_failed": totp_failed,
        "warning": "Save the new VAULT_ENCRYPTION_KEY to your env before the next restart.",
        "new_key_preview": new_key[:12] + "...",
        "event": event,
    }


@router.get("/admin/system/events")
async def admin_system_events(_admin: User = Depends(require_admin)):
    events = await db.system_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"events": events}


@router.get("/admin/audit")
async def admin_audit(_admin: User = Depends(require_admin)):
    logs = await db.audit_log.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"audit": logs}


# -----------------------------------------------------------------------------
# STREAMING PROVIDERS
# -----------------------------------------------------------------------------
@router.get("/admin/streaming/providers")
async def admin_streaming_providers(_admin: User = Depends(require_admin)):
    current = os.environ.get(
        "STREAMING_PROVIDER",
        "gcp-livestream" if live_stream_service.is_live_enabled() else "mock",
    )
    cost = await live_stream_service.active_channels_cost()
    return {
        "current": current,
        "gcp_configured": live_stream_service.is_live_enabled(),
        "active_cost": cost,
        "providers": [
            {"id": "gcp-livestream", "name": "Google Cloud Live Stream",
             "status": "active" if live_stream_service.is_live_enabled() else "available",
             "requires": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT",
                          "LIVESTREAM_GCS_BUCKET"]},
            {"id": "mux", "name": "Mux", "status": "available",
             "requires": ["MUX_TOKEN_ID", "MUX_TOKEN_SECRET"]},
            {"id": "aws-ivs", "name": "AWS IVS", "status": "available",
             "requires": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]},
            {"id": "cloudflare-stream", "name": "Cloudflare Stream", "status": "available",
             "requires": ["CF_ACCOUNT_ID", "CF_STREAM_TOKEN"]},
            {"id": "mock", "name": "Direct URL (mock)",
             "status": "active" if not live_stream_service.is_live_enabled() and current == "mock" else "available",
             "requires": []},
        ],
    }


@router.post("/admin/streaming/providers/switch")
async def admin_streaming_switch(body: Dict[str, str], _admin: User = Depends(require_admin)):
    target = body.get("provider_id")
    if target not in {"mux", "aws-ivs", "cloudflare-stream", "mock"}:
        raise HTTPException(status_code=400, detail="Unknown provider")
    event = {
        "id": str(uuid.uuid4()), "type": "streaming.provider.switch",
        "from": os.environ.get("STREAMING_PROVIDER", "mock"),
        "to": target, "actor": _admin.id, "created_at": now_iso(),
    }
    await db.system_events.insert_one(event.copy())
    return {"message": f"Provider switch scheduled to {target}", "event": event}
