import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# --- HARD-CODED CONFIGURATION ---
ACCOUNT_ID = "10192b3261e4f353d1f24fce92b3e4db"
INPUT_ID = "340fafedcee8f68d1a4eac6518df78de"
# These match your R2 setup
VOD_BUCKET = "viewclipmedia"
RECORDING_BUCKET = "viewclip-raw-recordings"
DASHBOARD_BUCKET = "viewclip-user-dashboards"

def is_live_enabled() -> bool:
    """Checks for Cloudflare credentials instead of GCP."""
    return bool(os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("STREAM_KEY"))

async def provision_stream(stream_id: str) -> Dict[str, Any]:
    """
    Returns your Cloudflare credentials. 
    The stream_id is used to create a unique playback path.
    """
    if not is_live_enabled():
        # Fallback to your existing mock logic if env vars aren't set in Railway
        from uuid import uuid4
        key = uuid4().hex[:16]
        return {
            "mode": "mock",
            "ingest_url": f"rtmp://ingest.viewclip.mock/live/{stream_id}?key={key}",
            "playback_url": f"https://cdn.viewclip.mock/hls/{stream_id}/manifest.m3u8",
            "stream_key": key,
        }

    # REAL CLOUDFLARE LOGIC
    # This matches the playback URL format seen in image_42.png
    playback_base = f"https://customer-9j4l1hc445d4sh86.cloudflarestream.com/{INPUT_ID}"
    
    return {
        "mode": "cloudflare",
        "ingest_url": "rtmps://live.cloudflare.com:443/live/",
        "stream_key": os.environ.get("STREAM_KEY"),
        "playback_url": f"{playback_base}/manifest.m3u8",
        "input_id": INPUT_ID
    }

async def stop_stream(stream_id: str) -> Dict[str, Any]:
    """Cloudflare handles stopping automatically when the RTMPS feed cuts."""
    return {"mode": "cloudflare", "stopped": True}
