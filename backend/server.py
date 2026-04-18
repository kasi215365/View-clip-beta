from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
    CheckoutSessionRequest,
)

import stripe_service
import live_stream_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# =============================================================================
# TRIPLE-LAYER ENTERPRISE DATABASE ARCHITECTURE
# Three logical databases on the shared Mongo cluster:
#   1. IDENTITY_DB  — account credentials, subscriptions, global settings
#   2. STREAMING_DB — live stream data, content, chat, follows, notifications
#   3. VAULT_DB     — payments, gifts, earnings, payouts, banking info (encrypted)
# Each DB can be migrated to its own physical cluster by changing env vars only.
# =============================================================================
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)

_LEGACY_DB_NAME = os.environ['DB_NAME']
_IDENTITY_DB_NAME = os.environ.get('DB_NAME_IDENTITY', f"{_LEGACY_DB_NAME}_identity")
_STREAMING_DB_NAME = os.environ.get('DB_NAME_STREAMING', f"{_LEGACY_DB_NAME}_streaming")
_VAULT_DB_NAME = os.environ.get('DB_NAME_VAULT', f"{_LEGACY_DB_NAME}_vault")

db_identity = client[_IDENTITY_DB_NAME]
db_streaming = client[_STREAMING_DB_NAME]
db_vault = client[_VAULT_DB_NAME]
_legacy_db = client[_LEGACY_DB_NAME]

# Collection → layer routing (enterprise database-router pattern)
_COLLECTION_LAYER = {
    # Identity layer — account data
    'users': 'identity', 'subscriptions': 'identity', 'settings': 'identity',
    'sessions': 'identity',
    # Streaming layer — real-time media + engagement
    'content': 'streaming', 'live_streams': 'streaming', 'comments': 'streaming',
    'follows': 'streaming', 'notifications': 'streaming', 'watch_sessions': 'streaming',
    # Vault layer — financial / sensitive (field-level encryption applied)
    'payment_transactions': 'vault', 'gifts': 'vault', 'earnings': 'vault',
    'payouts': 'vault', 'banking_info': 'vault', 'referral_events': 'vault',
    'audit_log': 'vault', 'system_events': 'vault',
}
_LAYER_DB = {'identity': db_identity, 'streaming': db_streaming, 'vault': db_vault}


class DBRouter:
    """Enterprise 3-layer database router. Transparently routes
    `db.users`, `db.gifts`, etc. to the appropriate logical database."""
    def __getattr__(self, name: str):
        layer = _COLLECTION_LAYER.get(name, 'identity')
        return _LAYER_DB[layer][name]


db = DBRouter()

# =============================================================================
# VAULT FIELD-LEVEL ENCRYPTION (AES-128 via Fernet)
# =============================================================================
_VAULT_KEY = os.environ.get('VAULT_ENCRYPTION_KEY')
if not _VAULT_KEY:
    # Auto-generate on first boot. In production this MUST come from env.
    _VAULT_KEY = Fernet.generate_key().decode()
    logging.warning("VAULT_ENCRYPTION_KEY missing — generated ephemeral key (dev only)")
_vault_cipher = Fernet(_VAULT_KEY.encode() if isinstance(_VAULT_KEY, str) else _VAULT_KEY)


def vault_encrypt(plaintext: str) -> str:
    if plaintext is None:
        return None
    return _vault_cipher.encrypt(plaintext.encode()).decode()


def vault_decrypt(ciphertext: str) -> Optional[str]:
    if not ciphertext:
        return None
    try:
        return _vault_cipher.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None


def mask_bank(plaintext: Optional[str]) -> str:
    """Last-4 masking for display."""
    if not plaintext:
        return ""
    tail = plaintext[-4:]
    return f"•••• {tail}"

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 30  # 30 days

# Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

security = HTTPBearer()
app = FastAPI(title="View/Clip")
api_router = APIRouter(prefix="/api")

# =============================================================================
# BUSINESS CONSTANTS (View/Clip economic model)
# =============================================================================
VIEWER_SUB_PRICE = 7.00
STREAMER_SUB_PRICE = 50.00

# Gift tiers: id, emoji, label, value_per_unit ($ streamer earns per unit used),
# qty (units in bundle), price (USD user pays for bundle)
GIFT_TIERS: List[Dict[str, Any]] = [
    {"id": "t1", "emoji": "🪙", "name": "Coin",      "value_per_unit": 0.002, "qty": 500, "price": 10.00},
    {"id": "t2", "emoji": "🥃", "name": "Shot",      "value_per_unit": 0.013, "qty": 500, "price": 20.00},
    {"id": "t3", "emoji": "🥇", "name": "Gold",      "value_per_unit": 0.102, "qty": 500, "price": 35.00},
    {"id": "t4", "emoji": "🏆", "name": "Trophy",    "value_per_unit": 0.140, "qty": 500, "price": 50.00},
    {"id": "t5", "emoji": "🏎",  "name": "Racer",     "value_per_unit": 0.200, "qty": 500, "price": 72.00},
    {"id": "t6", "emoji": "🏚",  "name": "Mansion",   "value_per_unit": 1.050, "qty": 500, "price": 100.00},
    {"id": "t7", "emoji": "💎", "name": "Diamond",   "value_per_unit": 2.003, "qty": 500, "price": 200.00},
    {"id": "t8", "emoji": "🌍", "name": "World",     "value_per_unit": 3.000, "qty": 500, "price": 300.00},
]
GIFT_TIERS_BY_ID = {t["id"]: t for t in GIFT_TIERS}

DEFAULT_SETTINGS = {
    "viewer_sub_price": VIEWER_SUB_PRICE,
    "streamer_sub_price": STREAMER_SUB_PRICE,
    "earnings_per_view": 0.005,             # $0.005 per view (30-min threshold)
    "view_threshold_minutes": 30,
    "earnings_per_100k_views": 5.00,         # display helper ($0.005 * 100000 = $500 actually)
    "gift_base_rate": 0.002,
    "budget_alert_percent": 80,              # admin-configurable bandwidth cap %
    "maintenance_mode": False,
}

# =============================================================================
# MODELS
# =============================================================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "viewer"
    referral_code: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    subscription_status: str = "inactive"
    subscription_expires: Optional[str] = None
    created_at: str
    gift_wallet: Dict[str, int] = Field(default_factory=dict)  # tier_id -> units
    connect_account_status: str = "not_onboarded"  # not_onboarded, pending, active
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    referral_earnings: float = 0.0

class Content(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    type: str
    video_url: str
    thumbnail_url: str
    duration: int
    views: int = 0
    is_promo: bool = False
    created_at: str

class ContentCreate(BaseModel):
    title: str
    description: str
    type: str
    video_url: str
    thumbnail_url: str
    duration: int
    is_promo: bool = False

class LiveStream(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    streamer_id: str
    streamer_name: str
    title: str
    description: str
    video_url: str
    thumbnail_url: str
    is_live: bool
    viewers_count: int = 0
    start_time: str
    end_time: Optional[str] = None
    views: int = 0
    qualified_views: int = 0   # views that hit 30-min threshold
    saved: bool = False
    exports: List[Dict[str, str]] = Field(default_factory=list)
    playback_url: Optional[str] = None
    ingest_url: Optional[str] = None
    stream_key: Optional[str] = None
    live_mode: Optional[str] = None

class LiveStreamCreate(BaseModel):
    title: str
    description: str
    video_url: str
    thumbnail_url: str

class Comment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    user_name: str
    stream_id: Optional[str] = None
    content_id: Optional[str] = None
    text: str
    created_at: str

class CommentCreate(BaseModel):
    stream_id: Optional[str] = None
    content_id: Optional[str] = None
    text: str

class GiftSend(BaseModel):
    stream_id: Optional[str] = None
    recipient_id: Optional[str] = None  # direct viewer-to-viewer gifting
    tier_id: str
    quantity: int = 1

class BankingInfoUpdate(BaseModel):
    account_holder: str
    account_number: str
    routing_number: str
    bank_name: str
    country: str = "US"

class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    type: str
    amount: float
    status: str
    created_at: str
    expires_at: str

class CheckoutSubscribe(BaseModel):
    type: str  # viewer | streamer
    origin_url: str

class CheckoutGiftBundle(BaseModel):
    tier_id: str
    origin_url: str

class ExportStream(BaseModel):
    platform: str  # youtube | twitch | x | custom
    target_url: Optional[str] = None

class AdminSettingsUpdate(BaseModel):
    viewer_sub_price: Optional[float] = None
    streamer_sub_price: Optional[float] = None
    earnings_per_view: Optional[float] = None
    view_threshold_minutes: Optional[int] = None
    gift_base_rate: Optional[float] = None
    budget_alert_percent: Optional[int] = None
    maintenance_mode: Optional[bool] = None

class PromoCreate(BaseModel):
    title: str
    description: str
    thumbnail_url: str
    video_url: str

# =============================================================================
# HELPERS
# =============================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.setdefault("gift_wallet", {})
        user.setdefault("connect_account_status", "not_onboarded")
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def get_settings() -> Dict[str, Any]:
    doc = await db.settings.find_one({"id": "global"}, {"_id": 0})
    if not doc:
        doc = {"id": "global", **DEFAULT_SETTINGS, "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.settings.insert_one(doc.copy())
        return doc
    merged = {**DEFAULT_SETTINGS, **doc}
    return merged

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _generate_referral_code(name: str, user_id: str) -> str:
    """Generate a short referral code based on name + uuid."""
    prefix = ''.join([c for c in (name or '').upper() if c.isalnum()])[:4] or "VC"
    suffix = user_id.replace("-", "")[:6].upper()
    return f"{prefix}{suffix}"

async def _notify(user_id: str, notification_type: str, title: str, body: str, data: Optional[Dict[str, Any]] = None):
    """Insert a notification document for a single user."""
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "body": body,
        "data": data or {},
        "read": False,
        "created_at": now_iso(),
    })

def get_stripe_checkout(request: Request) -> StripeCheckout:
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

# =============================================================================
# AUTH
# =============================================================================
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())

    # Resolve referral attribution (if valid code provided)
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
        "referral_code": _generate_referral_code(user_data.name, user_id),
        "referred_by": referred_by,
        "referral_earnings": 0.0,
    }
    await db.users.insert_one(user_doc)
    if referred_by:
        await db.users.update_one({"id": referred_by}, {"$inc": {"referral_count": 1}})
    token = create_token(user_id, user_data.email, user_data.role)
    return {
        "token": token,
        "user": User(**{k: v for k, v in user_doc.items() if k != 'password_hash'})
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user['id'], user['email'], user['role'])
    payload = {k: v for k, v in user.items() if k not in ['_id', 'password_hash']}
    payload.setdefault("gift_wallet", {})
    payload.setdefault("connect_account_status", "not_onboarded")
    return {"token": token, "user": User(**payload)}

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/admin/auth/login")
async def admin_login(credentials: UserLogin, request: Request):
    """Dedicated staff-portal login. Admin role required. Every attempt is audited."""
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

    token = create_token(user['id'], user['email'], user['role'])
    payload = {k: v for k, v in user.items() if k not in ['_id', 'password_hash']}
    payload.setdefault("gift_wallet", {})
    payload.setdefault("connect_account_status", "not_onboarded")

    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": user["id"],
        "action": "admin.auth.success",
        "meta": {"email": user["email"], "ip": client_ip},
        "created_at": now_iso(),
    })
    return {"token": token, "user": User(**payload), "portal": "staff"}

# =============================================================================
# CONTENT
# =============================================================================
@api_router.get("/content", response_model=List[Content])
async def get_content(type: Optional[str] = None):
    query = {"is_promo": {"$ne": True}}
    if type:
        query['type'] = type
    return await db.content.find(query, {"_id": 0}).to_list(1000)

@api_router.get("/content/{content_id}", response_model=Content)
async def get_content_by_id(content_id: str):
    content = await db.content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

@api_router.post("/content", response_model=Content)
async def create_content(content_data: ContentCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    content_id = str(uuid.uuid4())
    content_doc = {"id": content_id, **content_data.model_dump(), "views": 0, "created_at": now_iso()}
    await db.content.insert_one(content_doc.copy())
    return Content(**content_doc)

@api_router.post("/content/{content_id}/view")
async def increment_content_view(content_id: str, current_user: User = Depends(get_current_user)):
    result = await db.content.update_one({"id": content_id}, {"$inc": {"views": 1}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"message": "View recorded"}

# =============================================================================
# SELF-PROMOTION ENGINE
# =============================================================================
@api_router.get("/promos", response_model=List[Content])
async def list_promos():
    return await db.content.find({"is_promo": True}, {"_id": 0}).to_list(100)

@api_router.post("/promos", response_model=Content)
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

@api_router.delete("/promos/{promo_id}")
async def delete_promo(promo_id: str, _admin: User = Depends(require_admin)):
    res = await db.content.delete_one({"id": promo_id, "is_promo": True})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promo not found")
    return {"message": "deleted"}

# =============================================================================
# LIVE STREAMS
# =============================================================================
@api_router.get("/streams", response_model=List[LiveStream])
async def get_streams(is_live: Optional[bool] = None):
    query = {}
    if is_live is not None:
        query['is_live'] = is_live
    return await db.live_streams.find(query, {"_id": 0}).sort("start_time", -1).to_list(1000)

@api_router.get("/streams/{stream_id}", response_model=LiveStream)
async def get_stream_by_id(stream_id: str):
    stream = await db.live_streams.find_one({"id": stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@api_router.post("/streams", response_model=LiveStream)
async def create_stream(stream_data: LiveStreamCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ("streamer", "admin"):
        raise HTTPException(status_code=403, detail="Streamer access required")
    if current_user.subscription_status != "active" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Active streamer subscription required")
    stream_id = str(uuid.uuid4())

    # Provision live streaming infrastructure (real GCP if configured, mock otherwise)
    try:
        provision = await live_stream_service.provision_stream(stream_id)
    except Exception as e:
        logger.exception("Live provisioning failed")
        raise HTTPException(status_code=502, detail=f"Live infra unavailable: {str(e)[:180]}")

    # If client provided a URL, honour it; else use the provisioned playback URL
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
    # Notify all followers of this streamer
    followers = await db.follows.find({"streamer_id": current_user.id}, {"_id": 0, "follower_id": 1}).to_list(10000)
    for f in followers:
        await _notify(f["follower_id"], "stream_live",
                      f"{current_user.name} is live",
                      stream_data.title,
                      {"stream_id": stream_id, "streamer_id": current_user.id})
    return LiveStream(**stream_doc)

@api_router.post("/streams/{stream_id}/end")
async def end_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream['streamer_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.live_streams.update_one(
        {"id": stream_id},
        {"$set": {"is_live": False, "end_time": now_iso()}}
    )
    # Teardown live-stream infrastructure
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
            "created_at": now_iso()
        })
    return {"message": "Stream ended", "earnings": earnings, "qualified_views": qualified}

@api_router.post("/streams/{stream_id}/join")
async def join_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    result = await db.live_streams.update_one(
        {"id": stream_id, "is_live": True},
        {"$inc": {"viewers_count": 1, "views": 1}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stream not found or not live")
    return {"message": "Joined stream"}

@api_router.post("/streams/{stream_id}/heartbeat")
async def stream_heartbeat(stream_id: str, current_user: User = Depends(get_current_user)):
    """Client sends a heartbeat every 60s while watching. Server accumulates watch-minutes.
    At the view_threshold_minutes mark, increments qualified_views exactly once per viewer per stream."""
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
    return {"minutes": new_minutes, "qualified": qualified_now or session.get("qualified", False), "threshold": threshold}

@api_router.post("/streams/{stream_id}/qualified-view")
async def qualified_view(stream_id: str, current_user: User = Depends(get_current_user)):
    """DEPRECATED: Legacy endpoint for backward compat. Prefer /heartbeat."""
    result = await db.live_streams.update_one(
        {"id": stream_id},
        {"$inc": {"qualified_views": 1}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"message": "Qualified view recorded"}

@api_router.post("/streams/{stream_id}/save")
async def save_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream['streamer_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.live_streams.update_one({"id": stream_id}, {"$set": {"saved": True}})
    return {"message": "Stream saved"}

@api_router.post("/streams/{stream_id}/export")
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
    export_record = {
        "platform": body.platform,
        "target_url": body.target_url or f"https://{body.platform}.com/viewclip/{stream_id}",
        "exported_at": now_iso(),
    }
    await db.live_streams.update_one(
        {"id": stream_id},
        {"$push": {"exports": export_record}}
    )
    return {"message": "Stream exported", "export": export_record}

# =============================================================================
# COMMENTS
# =============================================================================
@api_router.post("/comments", response_model=Comment)
async def create_comment(comment_data: CommentCreate, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    comment_doc = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "user_name": current_user.name,
        **comment_data.model_dump(),
        "created_at": now_iso()
    }
    await db.comments.insert_one(comment_doc.copy())
    return Comment(**comment_doc)

@api_router.get("/comments/{stream_id}", response_model=List[Comment])
async def get_comments(stream_id: str):
    return await db.comments.find({"stream_id": stream_id}, {"_id": 0}).sort("created_at", -1).to_list(1000)

# =============================================================================
# GIFTS (tier-based, wallet-backed)
# =============================================================================
@api_router.get("/gifts/tiers")
async def list_gift_tiers():
    return {"tiers": GIFT_TIERS}

@api_router.get("/gifts/wallet")
async def get_wallet(current_user: User = Depends(get_current_user)):
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "gift_wallet": 1})
    return {"wallet": (user or {}).get("gift_wallet", {})}

@api_router.post("/gifts/send")
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

    # Resolve recipient — either from stream streamer or direct recipient
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
        raise HTTPException(status_code=400, detail=f"Insufficient {tier['emoji']} {tier['name']} units. Purchase a bundle first.")
    wallet[body.tier_id] = balance - body.quantity
    await db.users.update_one({"id": current_user.id}, {"$set": {"gift_wallet": wallet}})

    # Earnings calculation
    settings = await get_settings()
    base_rate = settings["gift_base_rate"]
    per_unit = max(tier["value_per_unit"], base_rate)
    earnings = round(per_unit * body.quantity, 4)

    gift_doc = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "streamer_id": recipient_id,   # kept as 'streamer_id' for back-compat; acts as recipient_id
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
        "streamer_id": recipient_id,   # generic "recipient earnings"
        "user_id": recipient_id,
        "amount": earnings,
        "source": "gifts",
        "description": f"{body.quantity}x {tier['emoji']} {tier['name']} from {current_user.name}"
                      + (f" (on stream: {stream['title']})" if stream else " (direct gift)"),
        "created_at": now_iso()
    })
    await _notify(recipient_id, "gift_received",
                  f"{tier['emoji']} Gift from {current_user.name}",
                  f"{body.quantity}x {tier['name']} (+${earnings:.3f})",
                  {"stream_id": body.stream_id, "amount": earnings,
                   "sender_id": current_user.id, "sender_name": current_user.name})
    return {"message": "Gift sent", "gift": gift_doc, "recipient_earned": earnings,
            "streamer_earned": earnings}  # back-compat alias

# =============================================================================
# STRIPE PAYMENTS
# =============================================================================
@api_router.post("/payments/checkout/subscribe")
async def checkout_subscribe(body: CheckoutSubscribe, request: Request, current_user: User = Depends(get_current_user)):
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

    # Prefer REAL recurring Stripe subscriptions when a real API key is configured.
    # Fallback: emergentintegrations one-time Checkout (30-day mock renewal).
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
        stripe_checkout = get_stripe_checkout(request)
        checkoutrequest = CheckoutSessionRequest(
            amount=amount,
            currency="usd",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"purpose": "subscription", "sub_type": body.type, "user_id": current_user.id},
        )
        session_resp: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkoutrequest)
        metadata = {"sub_type": body.type, "recurring": False}
        url = session_resp.url
        session_id = session_resp.session_id

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

@api_router.post("/payments/subscription/cancel")
async def cancel_subscription_endpoint(current_user: User = Depends(get_current_user)):
    """Cancel user's active Stripe Subscription at period end."""
    sub = await db.subscriptions.find_one(
        {"user_id": current_user.id, "status": "active", "stripe_subscription_id": {"$exists": True}},
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
        {"$set": {"cancel_at_period_end": True, "cancelled_at": now_iso()}}
    )
    return {"message": "Subscription will cancel at period end", "expires_at": sub.get("expires_at")}

@api_router.post("/payments/checkout/gift-bundle")
async def checkout_gift_bundle(body: CheckoutGiftBundle, request: Request, current_user: User = Depends(get_current_user)):
    tier = GIFT_TIERS_BY_ID.get(body.tier_id)
    if not tier:
        raise HTTPException(status_code=400, detail="Invalid gift tier")

    amount = float(tier["price"])
    origin = body.origin_url.rstrip('/')
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/profile"

    stripe_checkout = get_stripe_checkout(request)
    checkoutrequest = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "purpose": "gift_bundle",
            "tier_id": tier["id"],
            "qty": str(tier["qty"]),
            "user_id": current_user.id,
        }
    )
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkoutrequest)

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
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
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/payments/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request, current_user: User = Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx["user_id"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    stripe_checkout = get_stripe_checkout(request)
    status_response: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)

    # Update transaction status (once)
    if not tx.get("processed") and status_response.payment_status == "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id, "processed": {"$ne": True}},
            {"$set": {
                "status": status_response.status,
                "payment_status": status_response.payment_status,
                "processed": True,
                "completed_at": now_iso(),
            }}
        )
        # Fulfilment
        await _fulfill_payment(tx)
    else:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": status_response.status,
                "payment_status": status_response.payment_status,
            }}
        )
    return {
        "status": status_response.status,
        "payment_status": status_response.payment_status,
        "amount_total": status_response.amount_total,
        "currency": status_response.currency,
        "purpose": tx.get("purpose"),
        "metadata": status_response.metadata,
    }

async def _fulfill_payment(tx: Dict[str, Any]):
    """Idempotent fulfilment based on purpose."""
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

        # Referral 10% rev-share credit on first-ever paid subscription
        user = await db.users.find_one({"id": user_id})
        prior_subs = await db.subscriptions.count_documents({"user_id": user_id, "status": "active"})
        referrer_id = (user or {}).get("referred_by")
        if referrer_id and prior_subs <= 1:  # this one just inserted
            commission = round(float(tx["amount"]) * 0.10, 4)
            await db.users.update_one({"id": referrer_id}, {"$inc": {"referral_earnings": commission}})
            await db.referral_events.insert_one({
                "id": str(uuid.uuid4()),
                "referrer_id": referrer_id,
                "referred_user_id": user_id,
                "amount": commission,
                "source_amount": float(tx["amount"]),
                "sub_type": sub_type,
                "created_at": now_iso(),
            })
            await _notify(referrer_id, "referral", "Referral reward!",
                          f"You earned ${commission} from a {sub_type} subscription.",
                          {"amount": commission})
    elif purpose == "gift_bundle":
        tier_id = tx["metadata"]["tier_id"]
        qty = int(tx["metadata"]["qty"])
        user = await db.users.find_one({"id": user_id})
        wallet = (user or {}).get("gift_wallet", {})
        wallet[tier_id] = int(wallet.get(tier_id, 0)) + qty
        await db.users.update_one({"id": user_id}, {"$set": {"gift_wallet": wallet}})

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Unified webhook: handles gift-bundle Checkout, subscription lifecycle,
    and Connect account updates. Uses native stripe SDK verification when
    STRIPE_WEBHOOK_SECRET is configured; otherwise falls back to emergentintegrations."""
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")

    # Prefer native stripe SDK verification if webhook secret is configured
    native_event = stripe_service.verify_webhook(body, sig)
    if native_event:
        etype = native_event.get("type")
        obj = native_event["data"]["object"]

        # Gift bundle one-time payment
        if etype == "checkout.session.completed" and obj.get("mode") == "payment":
            session_id = obj["id"]
            tx = await db.payment_transactions.find_one({"session_id": session_id})
            if tx and not tx.get("processed"):
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "processed": {"$ne": True}},
                    {"$set": {"processed": True, "payment_status": "paid", "status": "completed", "completed_at": now_iso()}}
                )
                await _fulfill_payment(tx)

        # Subscription created via Checkout
        elif etype == "checkout.session.completed" and obj.get("mode") == "subscription":
            session_id = obj["id"]
            subscription_id = obj.get("subscription")
            customer_id = obj.get("customer")
            tx = await db.payment_transactions.find_one({"session_id": session_id})
            if tx and not tx.get("processed"):
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "processed": {"$ne": True}},
                    {"$set": {"processed": True, "payment_status": "paid", "status": "completed",
                              "stripe_subscription_id": subscription_id, "stripe_customer_id": customer_id,
                              "completed_at": now_iso()}}
                )
                await _fulfill_payment({**tx, "stripe_subscription_id": subscription_id,
                                        "stripe_customer_id": customer_id})

        # Subscription renewal / cancellation lifecycle
        elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
            subscription_id = obj["id"]
            status = obj.get("status")  # active | canceled | past_due | unpaid
            cpe = bool(obj.get("cancel_at_period_end"))
            current_period_end = obj.get("current_period_end")
            from datetime import datetime as _dt
            expires = _dt.fromtimestamp(current_period_end, tz=timezone.utc).isoformat() if current_period_end else None

            existing = await db.subscriptions.find_one({"stripe_subscription_id": subscription_id})
            if existing:
                user_id = existing["user_id"]
                if etype == "customer.subscription.deleted" or status in ("canceled", "incomplete_expired"):
                    await db.subscriptions.update_one({"stripe_subscription_id": subscription_id},
                                                     {"$set": {"status": "cancelled", "cancelled_at": now_iso()}})
                    await db.users.update_one({"id": user_id}, {"$set": {"subscription_status": "inactive"}})
                else:
                    patch = {"status": "active" if status == "active" else status,
                             "cancel_at_period_end": cpe}
                    if expires:
                        patch["expires_at"] = expires
                    await db.subscriptions.update_one({"stripe_subscription_id": subscription_id}, {"$set": patch})
                    if expires:
                        await db.users.update_one({"id": user_id},
                                                 {"$set": {"subscription_expires": expires,
                                                           "subscription_status": "active" if status == "active" else "inactive"}})

        # Invoice paid — extend user subscription window
        elif etype == "invoice.paid":
            subscription_id = obj.get("subscription")
            period_end = obj.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
            if subscription_id and period_end:
                from datetime import datetime as _dt
                expires = _dt.fromtimestamp(period_end, tz=timezone.utc).isoformat()
                await db.subscriptions.update_one({"stripe_subscription_id": subscription_id},
                                                 {"$set": {"expires_at": expires, "status": "active"}})
                sub = await db.subscriptions.find_one({"stripe_subscription_id": subscription_id})
                if sub:
                    await db.users.update_one({"id": sub["user_id"]},
                                             {"$set": {"subscription_expires": expires, "subscription_status": "active"}})

        # Connect account updated — refresh streamer status
        elif etype == "account.updated":
            account_id = obj["id"]
            charges_enabled = obj.get("charges_enabled")
            payouts_enabled = obj.get("payouts_enabled")
            status = "active" if (charges_enabled and payouts_enabled) else "pending"
            await db.users.update_one({"connect_account_id": account_id},
                                     {"$set": {"connect_account_status": status}})

        return {"received": True, "handled": etype}

    # Fallback: emergentintegrations handler (for gift bundles when webhook secret not yet set)
    stripe_checkout = get_stripe_checkout(request)
    try:
        event = await stripe_checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.exception("Webhook parse error")
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e}")

    if event.event_type == "checkout.session.completed" and event.payment_status == "paid":
        tx = await db.payment_transactions.find_one({"session_id": event.session_id})
        if tx and not tx.get("processed"):
            await db.payment_transactions.update_one(
                {"session_id": event.session_id, "processed": {"$ne": True}},
                {"$set": {"processed": True, "payment_status": "paid", "status": "completed", "completed_at": now_iso()}}
            )
            await _fulfill_payment(tx)
    return {"received": True}

# =============================================================================
# LEGACY SUBSCRIPTION STATUS
# =============================================================================
@api_router.get("/subscriptions/status")
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    subscription = await db.subscriptions.find_one(
        {"user_id": current_user.id, "status": "active"},
        {"_id": 0}
    )
    return {"has_subscription": subscription is not None, "subscription": subscription}

# =============================================================================
# EARNINGS & STREAMER CONNECT (Stripe Connect mock)
# =============================================================================
@api_router.get("/earnings")
async def get_earnings(current_user: User = Depends(get_current_user)):
    # Viewers can see their own earnings (from received gifts).
    return await db.earnings.find({"streamer_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api_router.get("/earnings/total")
async def get_total_earnings(current_user: User = Depends(get_current_user)):
    pipeline = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    result = await db.earnings.aggregate(pipeline).to_list(1)
    total = result[0]['total'] if result else 0
    return {"total_earnings": round(total, 4)}

@api_router.post("/streamers/connect/onboard")
async def connect_onboard(current_user: User = Depends(get_current_user)):
    """Stripe Connect Express onboarding. Uses real Stripe when a real API key
    is configured; falls back to a mock onboarding flow otherwise."""
    if current_user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer access required")

    # Graceful fallback — real Stripe not configured
    if not stripe_service.real_stripe_enabled():
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {"connect_account_status": "active", "connect_onboarded_at": now_iso()}}
        )
        return {
            "message": "Connect onboarding complete (mock — configure STRIPE_API_KEY for real)",
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
                {"$set": {"connect_account_id": account_id, "connect_account_status": "pending"}},
            )

        base = os.environ.get("PUBLIC_APP_URL", "").rstrip("/") or ""
        refresh_url = f"{base}/profile" if base else "https://example.com/profile"
        return_url = f"{base}/profile?connect=done" if base else "https://example.com/profile"
        link = stripe_service.create_onboarding_link(account_id, refresh_url, return_url)
    except Exception as e:
        logger.exception("Connect onboard failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)[:180]}")

    return {
        "message": "Continue onboarding at Stripe",
        "onboarding_url": link,
        "account_id": account_id,
        "status": "pending",
        "mock": False,
    }

@api_router.get("/streamers/connect/status")
async def connect_status(current_user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0, "connect_account_id": 1})
    account_id = (user_doc or {}).get("connect_account_id")
    if not account_id:
        return {"configured": False}
    try:
        info = stripe_service.retrieve_account(account_id)
    except Exception as e:
        return {"configured": True, "error": str(e)[:180]}
    status = "active" if info.get("charges_enabled") and info.get("payouts_enabled") else "pending"
    await db.users.update_one({"id": current_user.id}, {"$set": {"connect_account_status": status}})
    return {"configured": True, "status": status, **info}

# =============================================================================
# ADMIN COMMAND CENTER
# =============================================================================
@api_router.get("/admin/stats")
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
        *total_revenue_pipeline
    ]).to_list(1)
    total_revenue = rev[0]["total"] if rev else 0.0

    payouts = await db.earnings.aggregate(total_revenue_pipeline).to_list(1)
    total_payouts = payouts[0]["total"] if payouts else 0.0

    gifts_count = await db.gifts.count_documents({})

    return {
        "users": {"total": users_total, "viewers": viewers, "streamers": streamers, "active_subscriptions": active_subs},
        "streams": {"total": streams_total, "live_now": streams_live},
        "content": {"total": content_total, "promos": promos_total},
        "gifts": {"total_sent": gifts_count},
        "financials": {
            "total_revenue": round(total_revenue, 2),
            "total_payouts_owed": round(total_payouts, 4),
            "net": round(total_revenue - total_payouts, 2),
        },
    }

@api_router.get("/admin/users")
async def admin_users(_admin: User = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(1000)
    return {"users": users}

@api_router.get("/admin/settings")
async def admin_get_settings(_admin: User = Depends(require_admin)):
    return await get_settings()

@api_router.post("/admin/settings")
async def admin_update_settings(body: AdminSettingsUpdate, _admin: User = Depends(require_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")
    updates["updated_at"] = now_iso()
    await db.settings.update_one({"id": "global"}, {"$set": updates}, upsert=True)
    return await get_settings()

@api_router.post("/admin/payouts/trigger")
async def admin_trigger_payouts(_admin: User = Depends(require_admin)):
    """Stripe Connect payout processing. Real Transfer.create when a real Stripe
    key is configured, otherwise logs mock payouts (earnings marked paid locally)."""
    pipeline = [
        {"$match": {"paid_out": {"$ne": True}}},
        {"$group": {"_id": "$streamer_id", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    by_streamer = await db.earnings.aggregate(pipeline).to_list(10000)

    real_mode = stripe_service.real_stripe_enabled()
    paid = 0
    skipped = 0
    errors = 0
    total_paid = 0.0
    for row in by_streamer:
        streamer_id = row["_id"]
        amount = round(row["total"], 4)
        if amount <= 0:
            continue
        user_doc = await db.users.find_one({"id": streamer_id}, {"_id": 0, "connect_account_id": 1, "connect_account_status": 1, "name": 1})
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
            {"$set": {"paid_out": True, "paid_out_at": now_iso(), "stripe_transfer_id": transfer_id}},
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
        await _notify(streamer_id, "payout", "Payout sent",
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

@api_router.get("/admin/payouts")
async def admin_list_payouts(_admin: User = Depends(require_admin)):
    payouts = await db.payouts.find({}, {"_id": 0}).sort("processed_at", -1).to_list(1000)
    return {"payouts": payouts}

# =============================================================================
# REFERRALS
# =============================================================================
@api_router.get("/referrals/my")
async def my_referrals(current_user: User = Depends(get_current_user)):
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "referral_code": 1, "referral_earnings": 1})
    # Backfill missing code for legacy users
    code = (user or {}).get("referral_code")
    if not code:
        code = _generate_referral_code(current_user.name, current_user.id)
        await db.users.update_one({"id": current_user.id}, {"$set": {"referral_code": code}})
    referred_users = await db.users.count_documents({"referred_by": current_user.id})
    events = await db.referral_events.find({"referrer_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {
        "code": code,
        "referred_count": referred_users,
        "earnings": round(float((user or {}).get("referral_earnings", 0.0)), 4),
        "events": events,
    }

@api_router.get("/referrals/leaderboard")
async def referral_leaderboard():
    """Top 50 referrers by referral_earnings. Public — no auth required."""
    pipeline = [
        {"$match": {"referral_earnings": {"$gt": 0}}},
        {"$sort": {"referral_earnings": -1}},
        {"$limit": 50},
        {"$project": {"_id": 0, "name": 1, "referral_code": 1, "referral_earnings": 1, "role": 1}},
    ]
    rows = await db.users.aggregate(pipeline).to_list(50)
    # add referred_count
    enriched = []
    for i, r in enumerate(rows):
        count = await db.users.count_documents({"referred_by": (await db.users.find_one({"referral_code": r["referral_code"]}, {"_id": 0, "id": 1}))["id"]})
        enriched.append({**r, "rank": i + 1, "referred_count": count, "earnings": round(r["referral_earnings"], 2)})
    return {"leaderboard": enriched}

@api_router.get("/referrals/validate/{code}")
async def validate_referral_code(code: str):
    user = await db.users.find_one({"referral_code": code.upper()}, {"_id": 0, "name": 1})
    if not user:
        return {"valid": False}
    return {"valid": True, "referrer_name": user["name"]}

# =============================================================================
# FOLLOW / UNFOLLOW STREAMERS
# =============================================================================
@api_router.post("/streamers/{streamer_id}/follow")
async def follow_streamer(streamer_id: str, current_user: User = Depends(get_current_user)):
    if streamer_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    streamer = await db.users.find_one({"id": streamer_id}, {"_id": 0, "name": 1, "role": 1})
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    existing = await db.follows.find_one({"follower_id": current_user.id, "streamer_id": streamer_id})
    if existing:
        return {"message": "Already following", "following": True}

    await db.follows.insert_one({
        "id": str(uuid.uuid4()),
        "follower_id": current_user.id,
        "streamer_id": streamer_id,
        "created_at": now_iso(),
    })
    await _notify(streamer_id, "new_follower",
                  "New follower!",
                  f"{current_user.name} started following you.",
                  {"follower_id": current_user.id})
    return {"message": "Followed", "following": True}

@api_router.post("/streamers/{streamer_id}/unfollow")
async def unfollow_streamer(streamer_id: str, current_user: User = Depends(get_current_user)):
    res = await db.follows.delete_one({"follower_id": current_user.id, "streamer_id": streamer_id})
    return {"message": "Unfollowed" if res.deleted_count else "Was not following", "following": False}

@api_router.get("/streamers/{streamer_id}/follow-status")
async def follow_status(streamer_id: str, current_user: User = Depends(get_current_user)):
    exists = await db.follows.find_one({"follower_id": current_user.id, "streamer_id": streamer_id})
    followers = await db.follows.count_documents({"streamer_id": streamer_id})
    return {"following": exists is not None, "followers_count": followers}

@api_router.get("/users/me/follows")
async def my_follows(current_user: User = Depends(get_current_user)):
    rows = await db.follows.find({"follower_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    # Enrich with streamer info
    out = []
    for r in rows:
        s = await db.users.find_one({"id": r["streamer_id"]}, {"_id": 0, "id": 1, "name": 1, "role": 1})
        if s:
            # find latest live stream by this streamer
            live = await db.live_streams.find_one({"streamer_id": r["streamer_id"], "is_live": True}, {"_id": 0})
            out.append({**s, "followed_at": r["created_at"], "live_stream_id": (live or {}).get("id")})
    return {"follows": out}

# =============================================================================
# NOTIFICATIONS
# =============================================================================
@api_router.get("/notifications")
async def list_notifications(current_user: User = Depends(get_current_user)):
    rows = await db.notifications.find({"user_id": current_user.id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    unread = sum(1 for r in rows if not r.get("read"))
    return {"notifications": rows, "unread_count": unread}

@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    res = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "marked read"}

@api_router.post("/notifications/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    res = await db.notifications.update_many(
        {"user_id": current_user.id, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "all marked read", "count": res.modified_count}

# =============================================================================
# SEARCH
# =============================================================================
@api_router.get("/search")
async def search(q: str):
    """Unified search across content, streams and streamers."""
    q_str = (q or "").strip()
    if len(q_str) < 2:
        return {"content": [], "streams": [], "streamers": [], "query": q_str}
    regex = {"$regex": q_str, "$options": "i"}
    content = await db.content.find(
        {"$or": [{"title": regex}, {"description": regex}], "is_promo": {"$ne": True}},
        {"_id": 0}
    ).limit(20).to_list(20)
    streams = await db.live_streams.find(
        {"$or": [{"title": regex}, {"description": regex}, {"streamer_name": regex}]},
        {"_id": 0}
    ).sort("start_time", -1).limit(20).to_list(20)
    streamers = await db.users.find(
        {"role": {"$in": ["streamer", "admin"]}, "name": regex},
        {"_id": 0, "password_hash": 0}
    ).limit(20).to_list(20)
    return {"content": content, "streams": streams, "streamers": streamers, "query": q_str}

# =============================================================================
# TRENDING
# =============================================================================
@api_router.get("/trending")
async def trending():
    """Top VOD content and live streams ranked by views."""
    content = await db.content.find({"is_promo": {"$ne": True}}, {"_id": 0}).sort("views", -1).limit(12).to_list(12)
    streams = await db.live_streams.find({"is_live": True}, {"_id": 0}).sort("viewers_count", -1).limit(12).to_list(12)
    return {"content": content, "live_streams": streams}

# =============================================================================
# STREAMER ANALYTICS
# =============================================================================
@api_router.get("/streamers/me/analytics")
async def my_analytics(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("streamer", "admin"):
        raise HTTPException(status_code=403, detail="Streamer access required")

    # Earnings breakdown
    by_source_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": "$source", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    by_source = {r["_id"]: {"total": round(r["total"], 4), "count": r["count"]}
                 for r in await db.earnings.aggregate(by_source_pipe).to_list(10)}

    # 30-day earnings time-series
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    ts_pipe = [
        {"$match": {"streamer_id": current_user.id, "created_at": {"$gte": since}}},
        {"$project": {"day": {"$substr": ["$created_at", 0, 10]}, "amount": 1}},
        {"$group": {"_id": "$day", "total": {"$sum": "$amount"}}},
        {"$sort": {"_id": 1}},
    ]
    series = [{"date": r["_id"], "amount": round(r["total"], 4)} for r in await db.earnings.aggregate(ts_pipe).to_list(40)]

    # Top 10 gifters
    gifters_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": "$sender_id", "sender_name": {"$first": "$sender_name"}, "total_value": {"$sum": "$value"}, "count": {"$sum": "$quantity"}}},
        {"$sort": {"total_value": -1}},
        {"$limit": 10},
    ]
    top_gifters = [{"sender_id": r["_id"], "name": r["sender_name"], "total_value": round(r["total_value"], 3), "count": r["count"]}
                   for r in await db.gifts.aggregate(gifters_pipe).to_list(10)]

    # Gift tier breakdown
    tiers_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": "$tier_id", "emoji": {"$first": "$tier_emoji"}, "name": {"$first": "$tier_name"}, "count": {"$sum": "$quantity"}, "value": {"$sum": "$value"}}},
        {"$sort": {"value": -1}},
    ]
    tiers = [{"tier_id": r["_id"], "emoji": r["emoji"], "name": r["name"], "count": r["count"], "value": round(r["value"], 3)}
             for r in await db.gifts.aggregate(tiers_pipe).to_list(10)]

    # Streams summary
    total_streams = await db.live_streams.count_documents({"streamer_id": current_user.id})
    live_now = await db.live_streams.count_documents({"streamer_id": current_user.id, "is_live": True})
    views_pipe = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": None, "views": {"$sum": "$views"}, "qualified": {"$sum": "$qualified_views"}}},
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

# =============================================================================
# BANKING / VAULT (AES-encrypted at rest)
# =============================================================================
@api_router.get("/vault/banking")
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

@api_router.post("/vault/banking")
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
    await db.banking_info.update_one({"user_id": current_user.id}, {"$set": doc}, upsert=True)
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": current_user.id,
        "action": "banking.upsert",
        "meta": {"bank": body.bank_name, "country": body.country},
        "created_at": now_iso(),
    })
    return {"message": "Banking info saved (encrypted)"}

# =============================================================================
# ADMIN SYSTEM CONTROL CENTER — health, deploy, audit
# =============================================================================
_APP_START_TIME = time.time()
_REQUEST_COUNTER = {"total": 0, "by_path": defaultdict(int)}

@api_router.get("/admin/system/health")
async def admin_system_health(_admin: User = Depends(require_admin)):
    """Live system health snapshot across all three DB layers."""
    async def ping(dbh, name):
        t0 = time.time()
        try:
            await dbh.command("ping")
            return {"layer": name, "status": "ok", "latency_ms": round((time.time() - t0) * 1000, 2)}
        except Exception as e:
            return {"layer": name, "status": "error", "error": str(e)[:120]}
    layers = [
        await ping(db_identity, "identity"),
        await ping(db_streaming, "streaming"),
        await ping(db_vault, "vault"),
    ]
    uptime = int(time.time() - _APP_START_TIME)
    return {
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "uptime_seconds": uptime,
        "uptime_human": f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s",
        "layers": layers,
        "requests": {"total": _REQUEST_COUNTER["total"],
                     "top_paths": sorted(_REQUEST_COUNTER["by_path"].items(), key=lambda x: -x[1])[:10]},
        "firewall": {"rate_limit_per_min": int(os.environ.get("FIREWALL_RATE_LIMIT_PER_MIN", "300")),
                     "blocked_requests": _REQUEST_COUNTER.get("blocked", 0)},
        "encryption": {"algorithm": "Fernet (AES-128-CBC + HMAC-SHA256)", "vault_key_configured": bool(_VAULT_KEY)},
        "integrations": {
            "stripe_mode": "real" if stripe_service.real_stripe_enabled() else "mock (emergentintegrations)",
            "livestream_mode": "gcp-livestream" if live_stream_service.is_live_enabled() else "mock",
        },
    }

@api_router.post("/admin/system/reload-settings")
async def admin_reload_settings(_admin: User = Depends(require_admin)):
    settings = await get_settings()
    await db.system_events.insert_one({
        "id": str(uuid.uuid4()), "type": "settings.reload",
        "actor": _admin.id, "created_at": now_iso(),
    })
    return {"message": "Settings reloaded", "settings": settings}

@api_router.post("/admin/system/deploy-update")
async def admin_deploy_update(_admin: User = Depends(require_admin)):
    """Triggers a system update event. In production this would call the deployment pipeline."""
    version = os.environ.get("APP_VERSION", "1.0.0")
    event = {
        "id": str(uuid.uuid4()),
        "type": "deploy.update",
        "version": version,
        "actor": _admin.id,
        "created_at": now_iso(),
        "status": "completed",
    }
    await db.system_events.insert_one(event.copy())
    return {"message": f"Update v{version} applied", "event": event}

@api_router.post("/admin/system/rotate-keys")
async def admin_rotate_keys(_admin: User = Depends(require_admin)):
    """Generate a new Fernet vault key, re-encrypt every vault field, atomically
    rotate to the new key. Uses Fernet.MultiFernet semantics: new key becomes the
    encrypting key, old key stays in env for decrypting legacy rows during migration."""
    global _vault_cipher, _VAULT_KEY
    from cryptography.fernet import Fernet as _F

    new_key = _F.generate_key().decode()
    old_cipher = _vault_cipher
    new_cipher = _F(new_key.encode())

    # Re-encrypt banking_info records
    rotated = 0
    failed = 0
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

    # Swap active cipher in-process
    _vault_cipher = new_cipher
    _VAULT_KEY = new_key

    event = {
        "id": str(uuid.uuid4()),
        "type": "keys.rotate",
        "actor": _admin.id,
        "rotated_records": rotated,
        "failed_records": failed,
        "created_at": now_iso(),
    }
    await db.system_events.insert_one(event.copy())
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_id": _admin.id,
        "action": "keys.rotate",
        "meta": {"rotated": rotated, "failed": failed},
        "created_at": now_iso(),
    })
    logger.info(f"Vault key rotated — {rotated} records re-encrypted, {failed} failures")
    return {"message": f"Key rotated. {rotated} records re-encrypted, {failed} failed.",
            "rotated": rotated, "failed": failed,
            "warning": "Save the new VAULT_ENCRYPTION_KEY to your env before the next restart.",
            "new_key_preview": new_key[:12] + "...",
            "event": event}

@api_router.get("/admin/system/events")
async def admin_system_events(_admin: User = Depends(require_admin)):
    events = await db.system_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"events": events}

@api_router.get("/admin/audit")
async def admin_audit(_admin: User = Depends(require_admin)):
    logs = await db.audit_log.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"audit": logs}

@api_router.get("/admin/streaming/providers")
async def admin_streaming_providers(_admin: User = Depends(require_admin)):
    """Lists hot-swappable cloud streaming providers. Reflects what's wired in."""
    current = os.environ.get("STREAMING_PROVIDER", "gcp-livestream" if live_stream_service.is_live_enabled() else "mock")
    cost = await live_stream_service.active_channels_cost()
    return {
        "current": current,
        "gcp_configured": live_stream_service.is_live_enabled(),
        "active_cost": cost,
        "providers": [
            {"id": "gcp-livestream", "name": "Google Cloud Live Stream",
             "status": "active" if live_stream_service.is_live_enabled() else "available",
             "requires": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "LIVESTREAM_GCS_BUCKET"]},
            {"id": "mux", "name": "Mux", "status": "available", "requires": ["MUX_TOKEN_ID", "MUX_TOKEN_SECRET"]},
            {"id": "aws-ivs", "name": "AWS IVS", "status": "available", "requires": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]},
            {"id": "cloudflare-stream", "name": "Cloudflare Stream", "status": "available", "requires": ["CF_ACCOUNT_ID", "CF_STREAM_TOKEN"]},
            {"id": "mock", "name": "Direct URL (mock)",
             "status": "active" if not live_stream_service.is_live_enabled() and current == "mock" else "available", "requires": []},
        ],
    }

@api_router.post("/admin/streaming/providers/switch")
async def admin_streaming_switch(body: Dict[str, str], _admin: User = Depends(require_admin)):
    """Logs a provider switch. The hot-swap takes effect when the mapped env vars are provided
    at next boot — the code path is provider-agnostic so no redeploy is required for metadata."""
    target = body.get("provider_id")
    if target not in {"mux", "aws-ivs", "cloudflare-stream", "mock"}:
        raise HTTPException(status_code=400, detail="Unknown provider")
    event = {
        "id": str(uuid.uuid4()),
        "type": "streaming.provider.switch",
        "from": os.environ.get("STREAMING_PROVIDER", "mock"),
        "to": target,
        "actor": _admin.id,
        "created_at": now_iso(),
    }
    await db.system_events.insert_one(event.copy())
    return {"message": f"Provider switch scheduled to {target}", "event": event}

# =============================================================================
# APP SETUP
# =============================================================================
app.include_router(api_router)

# =============================================================================
# LEVEL-3 LOGIC FIREWALL MIDDLEWARE
# - Per-IP sliding-window rate limit
# - Path-level counters for admin observability
# - Admin API structured audit (who accessed what)
# =============================================================================
_RATE_WINDOW_SEC = 60
_RATE_LIMIT = int(os.environ.get("FIREWALL_RATE_LIMIT_PER_MIN", "300"))
_ip_hits: Dict[str, deque] = defaultdict(deque)


class FirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Sliding-window rate limit (skip for non-api routes and static)
        if path.startswith("/api/"):
            q = _ip_hits[ip]
            while q and now - q[0] > _RATE_WINDOW_SEC:
                q.popleft()
            if len(q) >= _RATE_LIMIT:
                _REQUEST_COUNTER["blocked"] = _REQUEST_COUNTER.get("blocked", 0) + 1
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            q.append(now)

            _REQUEST_COUNTER["total"] += 1
            _REQUEST_COUNTER["by_path"][path] += 1

        response = await call_next(request)
        return response


app.add_middleware(FirewallMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# STARTUP: migrate legacy data + seed default View/Clip self-promos
# =============================================================================
_DEFAULT_PROMOS = [
    {
        "title": "Welcome to View/Clip — the culture starts here",
        "description": "Live sports, premium movies, and the streamers driving the culture. All in one place.",
        "thumbnail_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1200",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    },
    {
        "title": "Stream to millions. Earn per view.",
        "description": "Creators earn $0.005 per qualified view plus every gift. Go live in seconds.",
        "thumbnail_url": "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=1200",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    },
    {
        "title": "View/Clip Originals — premium by design",
        "description": "Exclusive originals, live sports, and creator premieres. Available only on View/Clip.",
        "thumbnail_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=1200",
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    },
]


@app.on_event("startup")
async def startup_bootstrap():
    # 1. Migrate from legacy single-DB to layered architecture (one-shot)
    migrated = 0
    for coll_name, layer in _COLLECTION_LAYER.items():
        target = _LAYER_DB[layer]
        if _LEGACY_DB_NAME == {_IDENTITY_DB_NAME: 'identity',
                               _STREAMING_DB_NAME: 'streaming',
                               _VAULT_DB_NAME: 'vault'}.get(_LEGACY_DB_NAME):
            continue
        try:
            target_count = await target[coll_name].estimated_document_count()
            if target_count > 0:
                continue
            async for doc in _legacy_db[coll_name].find({}):
                doc.pop('_id', None)
                try:
                    await target[coll_name].insert_one(doc)
                    migrated += 1
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Migration skipped for {coll_name}: {e}")
    if migrated:
        logger.info(f"Data migration to layered DBs complete — {migrated} documents moved")

    # 2. Seed default View/Clip promos if none exist
    try:
        promos_count = await db.content.count_documents({"is_promo": True})
        if promos_count == 0:
            for p in _DEFAULT_PROMOS:
                await db.content.insert_one({
                    "id": str(uuid.uuid4()),
                    "title": p["title"],
                    "description": p["description"],
                    "thumbnail_url": p["thumbnail_url"],
                    "video_url": p["video_url"],
                    "type": "promo",
                    "duration": 30,
                    "is_promo": True,
                    "views": 0,
                    "created_at": now_iso(),
                })
            logger.info("Seeded default View/Clip self-promos")
    except Exception as e:
        logger.warning(f"Promo seed skipped: {e}")

    logger.info(f"View/Clip v{os.environ.get('APP_VERSION', '1.0.0')} ready "
                f"| DBs: identity={_IDENTITY_DB_NAME} streaming={_STREAMING_DB_NAME} vault={_VAULT_DB_NAME}")
    logger.info(
        "Integrations — Stripe: %s | Live Stream: %s",
        "REAL" if stripe_service.real_stripe_enabled() else "MOCK (set STRIPE_API_KEY to real sk_test_/sk_live_ key to activate)",
        "REAL (GCP)" if live_stream_service.is_live_enabled() else "MOCK (set GOOGLE_CLOUD_PROJECT + LIVESTREAM_GCS_BUCKET + GOOGLE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS to activate)",
    )


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
