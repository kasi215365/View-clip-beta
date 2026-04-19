"""Vault router — banking info (AES-encrypted at rest)."""
import uuid

from fastapi import APIRouter, Depends

from core.auth import get_current_user
from core.crypto import mask_bank, vault_decrypt, vault_encrypt
from core.db import db
from core.helpers import now_iso
from core.models import BankingInfoUpdate, User

router = APIRouter(prefix="/api")


@router.get("/vault/banking")
async def get_banking(current_user: User = Depends(get_current_user)):
    doc = await db.banking_info.find_one({"user_id": current_user.id}, {"_id": 0})
    if not doc:
        return {"configured": False}
    return {
        "configured": True,
        "account_holder": doc.get("account_holder"),
        "bank_name": doc.get("bank_name"),
        "country": doc.get("country"),
        "account_number_masked": mask_bank(vault_decrypt(doc.get("account_number_enc"))),
        "routing_number_masked": mask_bank(vault_decrypt(doc.get("routing_number_enc"))),
        "updated_at": doc.get("updated_at"),
    }


@router.post("/vault/banking")
async def upsert_banking(body: BankingInfoUpdate, current_user: User = Depends(get_current_user)):
    doc = {
        "user_id": current_user.id,
        "account_holder": body.account_holder,
        "bank_name": body.bank_name,
        "country": body.country,
        "account_number_enc": vault_encrypt(body.account_number),
        "routing_number_enc": vault_encrypt(body.routing_number),
        "updated_at": now_iso(),
    }
    await db.banking_info.update_one(
        {"user_id": current_user.id}, {"$set": doc}, upsert=True
    )
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": current_user.id,
        "action": "banking.upsert",
        "meta": {"bank": body.bank_name, "country": body.country},
        "created_at": now_iso(),
    })
    return {"message": "Banking info saved (encrypted)"}
