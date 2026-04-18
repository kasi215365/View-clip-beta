"""Google Cloud Live Stream API service.
Graceful fallback: if credentials are missing, returns mock URLs so the app
works out-of-the-box. When `GOOGLE_CLOUD_PROJECT` + `LIVESTREAM_GCS_BUCKET`
+ credentials (either `GOOGLE_APPLICATION_CREDENTIALS` path OR
`GOOGLE_SERVICE_ACCOUNT_JSON` inline JSON) are set, real provisioning is
activated automatically.
"""
import os
import json
import logging
import tempfile
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
LOCATION = os.environ.get("LIVESTREAM_LOCATION", "us-central1")
GCS_BUCKET = os.environ.get("LIVESTREAM_GCS_BUCKET", "").strip()
CREDS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
_INLINE_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

# If caller pasted JSON inline, materialise it to a temp file and export the path.
if _INLINE_JSON and not CREDS_PATH:
    try:
        parsed = json.loads(_INLINE_JSON)
        tmp = tempfile.NamedTemporaryFile(prefix="gcp-sa-", suffix=".json", delete=False, mode="w")
        json.dump(parsed, tmp)
        tmp.close()
        CREDS_PATH = tmp.name
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH
        logger.info("GCP service account JSON materialised from env at %s", CREDS_PATH)
    except Exception as e:
        logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON parse failed: %s", e)

_live_client = None


def is_live_enabled() -> bool:
    return bool(PROJECT_ID and GCS_BUCKET and CREDS_PATH and os.path.exists(CREDS_PATH))


def _get_client():
    global _live_client
    if _live_client is not None:
        return _live_client
    if not is_live_enabled():
        return None
    try:
        from google.cloud.video import live_stream_v1
        _live_client = live_stream_v1.LivestreamServiceClient()
        return _live_client
    except Exception as e:
        logger.warning(f"Live Stream client init failed — staying in mock mode: {e}")
        return None


def _mock_provision(stream_id: str) -> Dict[str, Any]:
    """Fallback when GCP creds not configured."""
    key = uuid.uuid4().hex[:16]
    return {
        "mode": "mock",
        "ingest_url": f"rtmp://ingest.viewclip.mock/live/{stream_id}?key={key}",
        "playback_url": f"https://cdn.viewclip.mock/hls/{stream_id}/manifest.m3u8",
        "stream_key": key,
    }


async def provision_stream(stream_id: str) -> Dict[str, Any]:
    """Idempotently provision an RTMP Input + transcoding Channel.
    Returns {ingest_url, playback_url, mode}. In mock mode, returns simulated URLs."""
    client = _get_client()
    if client is None:
        return _mock_provision(stream_id)

    from google.cloud.video import live_stream_v1
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    input_id = f"vc-in-{stream_id[:20]}"
    channel_id = f"vc-ch-{stream_id[:20]}"
    input_name = f"{parent}/inputs/{input_id}"
    channel_name = f"{parent}/channels/{channel_id}"

    # Input
    try:
        input_resource = client.get_input(name=input_name)
    except Exception:
        input_obj = live_stream_v1.Input(type_=live_stream_v1.Input.Type.RTMP_PUSH)
        op = client.create_input(parent=parent, input=input_obj, input_id=input_id)
        input_resource = op.result(timeout=120)

    rtmp_addresses = list(getattr(input_resource, "uri", "") and [input_resource.uri] or [])
    if not rtmp_addresses:
        # Some SDK versions expose `preprocessing_config` or `uri`; best-effort fallback
        rtmp_addresses = [f"rtmp://{LOCATION}-livestream.googleapis.com/live/{input_id}"]
    ingest_url = rtmp_addresses[0]

    # Channel (+ start)
    try:
        channel_resource = client.get_channel(name=channel_name)
        if channel_resource.streaming_state.name != "STREAMING":
            try:
                client.start_channel(name=channel_name).result(timeout=180)
            except Exception as e:
                logger.warning(f"start_channel idempotent warning: {e}")
    except Exception:
        channel = live_stream_v1.Channel(
            input_attachments=[live_stream_v1.InputAttachment(key="primary", input=input_name)],
            output=live_stream_v1.Channel.Output(uri=f"gs://{GCS_BUCKET}/streams/{stream_id}/"),
            elementary_streams=[
                live_stream_v1.ElementaryStream(
                    key="es_video",
                    video_stream=live_stream_v1.VideoStream(
                        h264=live_stream_v1.VideoStream.H264CodecSettings(
                            profile="high", width_pixels=1280, height_pixels=720,
                            bitrate_bps=3_000_000, frame_rate=30,
                        ),
                    ),
                ),
                live_stream_v1.ElementaryStream(
                    key="es_audio",
                    audio_stream=live_stream_v1.AudioStream(codec="aac", channel_count=2, bitrate_bps=160_000),
                ),
            ],
            mux_streams=[
                live_stream_v1.MuxStream(key="mux_video", elementary_streams=["es_video"]),
                live_stream_v1.MuxStream(key="mux_audio", elementary_streams=["es_audio"]),
            ],
            manifests=[
                live_stream_v1.Manifest(
                    file_name="manifest.m3u8",
                    type_=live_stream_v1.Manifest.ManifestType.HLS,
                    mux_streams=["mux_video", "mux_audio"],
                    max_segment_count=5,
                )
            ],
        )
        op = client.create_channel(parent=parent, channel=channel, channel_id=channel_id)
        op.result(timeout=300)
        try:
            client.start_channel(name=channel_name).result(timeout=180)
        except Exception as e:
            logger.warning(f"start_channel post-create warning: {e}")

    playback_url = f"https://storage.googleapis.com/{GCS_BUCKET}/streams/{stream_id}/manifest.m3u8"
    return {"mode": "gcp", "ingest_url": ingest_url, "playback_url": playback_url, "stream_key": None}


async def stop_stream(stream_id: str) -> Dict[str, Any]:
    """Stop channel + delete input. Safe no-op if running in mock mode or already stopped."""
    client = _get_client()
    if client is None:
        return {"mode": "mock", "stopped": True}

    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    input_name = f"{parent}/inputs/vc-in-{stream_id[:20]}"
    channel_name = f"{parent}/channels/vc-ch-{stream_id[:20]}"

    try:
        client.stop_channel(name=channel_name).result(timeout=300)
    except Exception as e:
        logger.warning(f"stop_channel warning: {e}")
    try:
        client.delete_channel(name=channel_name).result(timeout=120)
    except Exception as e:
        logger.warning(f"delete_channel warning: {e}")
    try:
        client.delete_input(name=input_name).result(timeout=120)
    except Exception as e:
        logger.warning(f"delete_input warning: {e}")

    return {"mode": "gcp", "stopped": True}


async def active_channels_cost() -> Dict[str, Any]:
    """Admin helper — list currently active GCP channels for cost visibility."""
    client = _get_client()
    if client is None:
        return {"mode": "mock", "active_channels": 0, "estimated_hourly_cost": 0.0}
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    try:
        rows = list(client.list_channels(parent=parent))
        active = [c for c in rows if c.streaming_state.name == "STREAMING"]
        return {
            "mode": "gcp",
            "active_channels": len(active),
            "estimated_hourly_cost": round(len(active) * 0.45, 2),  # ~$0.45/hr for 720p
            "estimated_monthly_cost": round(len(active) * 0.45 * 24 * 30, 2),
        }
    except Exception as e:
        return {"mode": "gcp", "error": str(e)[:120]}
