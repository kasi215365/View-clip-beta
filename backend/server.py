from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 30  # 30 days

security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "viewer"  # viewer, streamer, admin

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    subscription_status: str = "inactive"  # active, inactive
    subscription_expires: Optional[str] = None
    created_at: str

class Content(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    description: str
    type: str  # movie, tv-show, sport
    video_url: str
    thumbnail_url: str
    duration: int  # in seconds
    views: int = 0
    created_at: str

class ContentCreate(BaseModel):
    title: str
    description: str
    type: str
    video_url: str
    thumbnail_url: str
    duration: int

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
    saved: bool = False

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

class Gift(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    sender_id: str
    sender_name: str
    streamer_id: str
    stream_id: str
    amount: float
    created_at: str

class GiftCreate(BaseModel):
    stream_id: str
    amount: float

class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    type: str  # viewer, streamer
    amount: float
    status: str  # active, expired
    created_at: str
    expires_at: str

class SubscriptionCreate(BaseModel):
    type: str  # viewer, streamer

class Earning(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    streamer_id: str
    amount: float
    source: str  # views, gifts
    description: str
    created_at: str

# Helper Functions
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
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth Routes
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "subscription_status": "inactive",
        "subscription_expires": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
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
    return {
        "token": token,
        "user": User(**{k: v for k, v in user.items() if k not in ['_id', 'password_hash']})
    }

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Content Routes
@api_router.get("/content", response_model=List[Content])
async def get_content(type: Optional[str] = None):
    query = {}
    if type:
        query['type'] = type
    
    content_list = await db.content.find(query, {"_id": 0}).to_list(1000)
    return content_list

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
    content_doc = {
        "id": content_id,
        **content_data.model_dump(),
        "views": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.content.insert_one(content_doc)
    return Content(**content_doc)

@api_router.post("/content/{content_id}/view")
async def increment_content_view(content_id: str, current_user: User = Depends(get_current_user)):
    result = await db.content.update_one(
        {"id": content_id},
        {"$inc": {"views": 1}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {"message": "View recorded"}

# Live Stream Routes
@api_router.get("/streams", response_model=List[LiveStream])
async def get_streams(is_live: Optional[bool] = None):
    query = {}
    if is_live is not None:
        query['is_live'] = is_live
    
    streams = await db.live_streams.find(query, {"_id": 0}).sort("start_time", -1).to_list(1000)
    return streams

@api_router.get("/streams/{stream_id}", response_model=LiveStream)
async def get_stream_by_id(stream_id: str):
    stream = await db.live_streams.find_one({"id": stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@api_router.post("/streams", response_model=LiveStream)
async def create_stream(stream_data: LiveStreamCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "streamer" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Streamer access required")
    
    if current_user.subscription_status != "active" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Active streamer subscription required")
    
    stream_id = str(uuid.uuid4())
    stream_doc = {
        "id": stream_id,
        "streamer_id": current_user.id,
        "streamer_name": current_user.name,
        **stream_data.model_dump(),
        "is_live": True,
        "viewers_count": 0,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "views": 0,
        "saved": False
    }
    
    await db.live_streams.insert_one(stream_doc)
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
        {"$set": {
            "is_live": False,
            "end_time": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Calculate earnings from views
    views = stream['views']
    earnings_per_100k = 0.03
    earnings = (views / 100000) * earnings_per_100k
    
    if earnings > 0:
        earning_doc = {
            "id": str(uuid.uuid4()),
            "streamer_id": current_user.id,
            "amount": earnings,
            "source": "views",
            "description": f"Earnings from stream: {stream['title']}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.earnings.insert_one(earning_doc)
    
    return {"message": "Stream ended", "earnings": earnings}

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

@api_router.post("/streams/{stream_id}/save")
async def save_stream(stream_id: str, current_user: User = Depends(get_current_user)):
    stream = await db.live_streams.find_one({"id": stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if stream['streamer_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.live_streams.update_one(
        {"id": stream_id},
        {"$set": {"saved": True}}
    )
    
    return {"message": "Stream saved"}

# Comment Routes
@api_router.post("/comments", response_model=Comment)
async def create_comment(comment_data: CommentCreate, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    
    comment_id = str(uuid.uuid4())
    comment_doc = {
        "id": comment_id,
        "user_id": current_user.id,
        "user_name": current_user.name,
        **comment_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.comments.insert_one(comment_doc)
    return Comment(**comment_doc)

@api_router.get("/comments/{stream_id}", response_model=List[Comment])
async def get_comments(stream_id: str):
    comments = await db.comments.find({"stream_id": stream_id}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return comments

# Gift Routes
@api_router.post("/gifts", response_model=Gift)
async def send_gift(gift_data: GiftCreate, current_user: User = Depends(get_current_user)):
    if current_user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")
    
    stream = await db.live_streams.find_one({"id": gift_data.stream_id})
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    gift_id = str(uuid.uuid4())
    gift_doc = {
        "id": gift_id,
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "streamer_id": stream['streamer_id'],
        **gift_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.gifts.insert_one(gift_doc)
    
    # Calculate earnings from gift
    earnings = gift_data.amount * 0.002
    earning_doc = {
        "id": str(uuid.uuid4()),
        "streamer_id": stream['streamer_id'],
        "amount": earnings,
        "source": "gifts",
        "description": f"Gift from {current_user.name}",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.earnings.insert_one(earning_doc)
    
    return Gift(**gift_doc)

# Subscription Routes
@api_router.post("/subscriptions/subscribe")
async def subscribe(sub_data: SubscriptionCreate, current_user: User = Depends(get_current_user)):
    amount = 7.0 if sub_data.type == "viewer" else 100.0
    
    # Mock payment processing
    sub_id = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    
    sub_doc = {
        "id": sub_id,
        "user_id": current_user.id,
        "type": sub_data.type,
        "amount": amount,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at
    }
    
    await db.subscriptions.insert_one(sub_doc)
    
    # Update user subscription status
    update_data = {
        "subscription_status": "active",
        "subscription_expires": expires_at
    }
    
    if sub_data.type == "streamer":
        update_data["role"] = "streamer"
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": update_data}
    )
    
    return {"message": "Subscription activated", "subscription": Subscription(**sub_doc)}

@api_router.get("/subscriptions/status")
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    subscription = await db.subscriptions.find_one(
        {"user_id": current_user.id, "status": "active"},
        {"_id": 0}
    )
    
    return {
        "has_subscription": subscription is not None,
        "subscription": subscription
    }

# Earnings Routes
@api_router.get("/earnings", response_model=List[Earning])
async def get_earnings(current_user: User = Depends(get_current_user)):
    if current_user.role != "streamer" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Streamer access required")
    
    earnings = await db.earnings.find(
        {"streamer_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    return earnings

@api_router.get("/earnings/total")
async def get_total_earnings(current_user: User = Depends(get_current_user)):
    if current_user.role != "streamer" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Streamer access required")
    
    pipeline = [
        {"$match": {"streamer_id": current_user.id}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    
    result = await db.earnings.aggregate(pipeline).to_list(1)
    total = result[0]['total'] if result else 0
    
    return {"total_earnings": total}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
