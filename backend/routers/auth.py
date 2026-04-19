"""Authentication router — user auth + admin staff-portal login + TOTP 2FA."""
import base64
import io
import uuid
from typing import Dict

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import (
    create_token, get_current_user, hash_password,
    require_admin, verify_password,
)
from core.crypto import vault_decrypt, vault_encrypt
from core.db import db
from core.helpers import (
    check_admin_anomalies, generate_recovery_codes, generate_referral_code,
    hash_recovery_code, notify, now_iso, verify_recovery_code,
)
from core.models import AdminLogin, User, UserLogin, UserRegister

router = APIRouter(prefix="/api")


@router.post("/auth/register")
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())

    referred_by = None
    if user_data.referral_code:
        referrer = await db.users.find_one({"referral_code": user_data.referral_code.upper()})
        if referrer:
            referred_by = referrer["id"]

    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "subscription_status": "inactive",
        "subscription_expires": None,
        "created_at": now_iso(),
        "gift_wallet": {},
        "connect_account_status": "not_onboarded",
        "referral_code": generate_referral_code(user_data.name, user_id),
        "referred_by": referred_by,
        "referral_earnings": 0.0,
    }
    await db.users.insert_one(user_doc)
    if referred_by:
        await db.users.update_one({"id": referred_by}, {"$inc": {"referral_count": 1}})
    token = create_token(user_id, user_data.email, user_data.role)
    return {
        "token": token,
        "user": User(**{k: v for k, v in user_doc.items() if k != 'password_hash'}),
    }


@router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user['id'], user['email'], user['role'])
    payload = {k: v for k, v in user.items() if k not in ['_id', 'password_hash']}
    payload.setdefault("gift_wallet", {})
    payload.setdefault("connect_account_status", "not_onboarded")
    return {"token": token, "user": User(**payload)}


@router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/admin/auth/login")
async def admin_login(credentials: AdminLogin, request: Request):
    """Staff-portal login. Admin role + TOTP 2FA (if enabled). Every attempt audited."""
    user = await db.users.find_one({"email": credentials.email})
    client_ip = request.client.host if request.client else "unknown"

    if not user or not verify_password(credentials.password, user['password_hash']):
        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "actor_id": None,
            "action": "admin.auth.failed",
            "meta": {"email": credentials.email, "reason": "bad_credentials", "ip": client_ip},
            "created_at": now_iso(),
        })
        await check_admin_anomalies(user.get("id") if user else "", credentials.email, client_ip, success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.get("role") != "admin":
        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "actor_id": user["id"],
            "action": "admin.auth.denied",
            "meta": {"email": credentials.email, "reason": "not_admin", "ip": client_ip},
            "created_at": now_iso(),
        })
        raise HTTPException(status_code=403, detail="Admin access required")

    # TOTP 2FA challenge when enabled
    if user.get("totp_enabled"):
        if not credentials.totp_code:
            return {"require_2fa": True, "message": "Enter 6-digit code from your authenticator app"}

        stored_secret = user.get("totp_secret")
        plain_secret = vault_decrypt(stored_secret) if stored_secret else None
        verified = False
        recovery_used = -1

        code_clean = credentials.totp_code.replace("-", "").replace(" ", "").upper()
        if len(code_clean) == 6 and code_clean.isdigit() and plain_secret:
            verified = pyotp.TOTP(plain_secret).verify(credentials.totp_code, valid_window=1)
        elif len(code_clean) >= 12:
            recovery_used = verify_recovery_code(credentials.totp_code, user.get("totp_recovery_codes") or [])
            verified = recovery_used >= 0

        if not verified:
            await db.audit_log.insert_one({
                "id": str(uuid.uuid4()),
                "actor_id": user["id"],
                "action": "admin.auth.2fa_failed",
                "meta": {"email": credentials.email, "ip": client_ip},
                "created_at": now_iso(),
            })
            await check_admin_anomalies(user["id"], credentials.email, client_ip, success=False)
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

        if recovery_used >= 0:
            codes = list(user.get("totp_recovery_codes") or [])
            codes.pop(recovery_used)
            await db.users.update_one({"id": user["id"]}, {"$set": {"totp_recovery_codes": codes}})
            await db.audit_log.insert_one({
                "id": str(uuid.uuid4()),
                "actor_id": user["id"],
                "action": "admin.auth.recovery_used",
                "meta": {"email": credentials.email, "ip": client_ip, "remaining": len(codes)},
                "created_at": now_iso(),
            })
            await notify(user["id"], "security_anomaly",
                         "Recovery code used",
                         f"A recovery code was used to sign in from {client_ip}. {len(codes)} codes remain.",
                         {"kind": "recovery_used", "remaining": len(codes)})

    token = create_token(user['id'], user['email'], user['role'])
    payload = {k: v for k, v in user.items()
               if k not in ['_id', 'password_hash', 'totp_secret', 'totp_secret_pending', 'totp_recovery_codes']}
    payload.setdefault("gift_wallet", {})
    payload.setdefault("connect_account_status", "not_onboarded")

    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": user["id"],
        "action": "admin.auth.success",
        "meta": {"email": user["email"], "ip": client_ip, "twofa": bool(user.get("totp_enabled"))},
        "created_at": now_iso(),
    })
    await check_admin_anomalies(user["id"], user["email"], client_ip, success=True)
    return {"token": token, "user": User(**payload), "portal": "staff"}


@router.post("/admin/auth/2fa/setup")
async def admin_2fa_setup(_admin: User = Depends(require_admin)):
    secret = pyotp.random_base32()
    issuer = "View/Clip Staff"
    uri = pyotp.TOTP(secret).provisioning_uri(name=_admin.email, issuer_name=issuer)

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    await db.users.update_one(
        {"id": _admin.id}, {"$set": {"totp_secret_pending": secret}}
    )
    return {
        "secret": secret,
        "provisioning_uri": uri,
        "qr_code_png_base64": f"data:image/png;base64,{qr_b64}",
        "issuer": issuer,
    }


@router.post("/admin/auth/2fa/enable")
async def admin_2fa_enable(body: Dict[str, str], _admin: User = Depends(require_admin)):
    code = (body.get("code") or "").strip()
    user = await db.users.find_one({"id": _admin.id}, {"_id": 0, "totp_secret_pending": 1})
    secret = (user or {}).get("totp_secret_pending")
    if not secret:
        raise HTTPException(status_code=400, detail="Run /admin/auth/2fa/setup first")
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")

    encrypted_secret = vault_encrypt(secret)
    plain_codes = generate_recovery_codes(10)
    hashed_codes = [hash_recovery_code(c) for c in plain_codes]

    await db.users.update_one(
        {"id": _admin.id},
        {"$set": {
            "totp_secret": encrypted_secret,
            "totp_enabled": True,
            "totp_recovery_codes": hashed_codes,
            "totp_recovery_generated_at": now_iso(),
         },
         "$unset": {"totp_secret_pending": ""}},
    )
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": _admin.id,
        "action": "admin.2fa.enabled",
        "meta": {"email": _admin.email, "recovery_codes_issued": len(plain_codes)},
        "created_at": now_iso(),
    })
    return {
        "message": "2FA enabled for your account",
        "recovery_codes": plain_codes,
        "recovery_codes_warning": "Save these codes in a secure place. They are shown only once and each works one time.",
    }


@router.post("/admin/auth/2fa/disable")
async def admin_2fa_disable(body: Dict[str, str], _admin: User = Depends(require_admin)):
    code = (body.get("code") or "").strip()
    user = await db.users.find_one({"id": _admin.id}, {"_id": 0, "totp_secret": 1, "totp_enabled": 1})
    if not (user or {}).get("totp_enabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    stored_secret = (user or {}).get("totp_secret")
    plain_secret = vault_decrypt(stored_secret) if stored_secret else None
    if not plain_secret or not pyotp.TOTP(plain_secret).verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")
    await db.users.update_one(
        {"id": _admin.id},
        {"$set": {"totp_enabled": False},
         "$unset": {"totp_secret": "", "totp_secret_pending": "",
                    "totp_recovery_codes": "", "totp_recovery_generated_at": ""}},
    )
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": _admin.id,
        "action": "admin.2fa.disabled",
        "meta": {"email": _admin.email},
        "created_at": now_iso(),
    })
    return {"message": "2FA disabled"}


@router.post("/admin/auth/2fa/recovery-codes/regenerate")
async def admin_2fa_regenerate_recovery_codes(body: Dict[str, str], _admin: User = Depends(require_admin)):
    code = (body.get("code") or "").strip()
    user = await db.users.find_one({"id": _admin.id}, {"_id": 0, "totp_secret": 1, "totp_enabled": 1})
    if not (user or {}).get("totp_enabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    stored_secret = (user or {}).get("totp_secret")
    plain_secret = vault_decrypt(stored_secret) if stored_secret else None
    if not plain_secret or not pyotp.TOTP(plain_secret).verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")

    plain_codes = generate_recovery_codes(10)
    hashed_codes = [hash_recovery_code(c) for c in plain_codes]
    await db.users.update_one(
        {"id": _admin.id},
        {"$set": {"totp_recovery_codes": hashed_codes,
                  "totp_recovery_generated_at": now_iso()}},
    )
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": _admin.id,
        "action": "admin.2fa.recovery_regenerated",
        "meta": {"email": _admin.email, "count": len(plain_codes)},
        "created_at": now_iso(),
    })
    return {
        "message": "Recovery codes regenerated. Previous codes are invalid.",
        "recovery_codes": plain_codes,
        "recovery_codes_warning": "Save these codes in a secure place. They are shown only once and each works one time.",
    }


@router.get("/admin/auth/2fa/status")
async def admin_2fa_status(_admin: User = Depends(require_admin)):
    user = await db.users.find_one(
        {"id": _admin.id}, {"_id": 0, "totp_enabled": 1, "totp_secret_pending": 1}
    )
    return {
        "enabled": bool((user or {}).get("totp_enabled")),
        "pending_setup": bool((user or {}).get("totp_secret_pending")),
    }
