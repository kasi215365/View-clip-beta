"""Pydantic models used across routers.

All response models use `ConfigDict(extra='ignore')` so unknown Mongo fields
(including `_id`) are silently dropped.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "viewer"
    referral_code: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    subscription_status: str = "inactive"
    subscription_expires: Optional[str] = None
    created_at: str
    gift_wallet: Dict[str, int] = Field(default_factory=dict)
    connect_account_status: str = "not_onboarded"  # not_onboarded | pending | active
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


class StreamExportRecord(BaseModel):
    """Export record stored in stream.exports array."""
    model_config = ConfigDict(extra="ignore")
    platform: str
    target_url: str
    mock: bool = True
    uploaded: bool = False
    note: Optional[str] = None
    exported_at: str


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
    qualified_views: int = 0
    saved: bool = False
    exports: List[StreamExportRecord] = Field(default_factory=list)
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
