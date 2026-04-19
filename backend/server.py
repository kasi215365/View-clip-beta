"""View/Clip — FastAPI app factory.

Thin composition layer:
  1. Imports FastAPI + env.
  2. Creates the `app`, mounts middleware.
  3. Mounts every router from `/app/backend/routers/`.
  4. Runs one-shot startup tasks (legacy→layered DB migration, promo seeding).

Everything else lives under `core/` (shared state) and `routers/` (endpoints).
"""
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Shared state — kept at module scope so tests can monkey-patch if needed.
import live_stream_service  # noqa: E402
import stripe_service        # noqa: E402
from core.db import (  # noqa: E402
    _COLLECTION_LAYER, _IDENTITY_DB_NAME, _LAYER_DB, _LEGACY_DB_NAME,
    _STREAMING_DB_NAME, _VAULT_DB_NAME, _legacy_db, client, db,
)
from core.helpers import now_iso  # noqa: E402
from core.middleware import FirewallMiddleware, RequestIDMiddleware  # noqa: E402

app = FastAPI(title="View/Clip")

# -----------------------------------------------------------------------------
# MIDDLEWARE — order matters: CORS last so it runs first (outermost wrapper).
# -----------------------------------------------------------------------------
app.add_middleware(FirewallMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# ROUTERS — every endpoint lives in backend/routers/<name>.py
# -----------------------------------------------------------------------------
from routers import (  # noqa: E402
    admin as _admin_router,
    auth as _auth_router,
    content as _content_router,
    earnings as _earnings_router,
    gifts as _gifts_router,
    health as _health_router,
    notifications as _notifications_router,
    oauth as _oauth_router,
    payments as _payments_router,
    social as _social_router,
    streaming as _streaming_router,
    vault as _vault_router,
)

for r in (
    _health_router, _auth_router, _content_router, _streaming_router,
    _gifts_router, _payments_router, _earnings_router, _vault_router,
    _admin_router, _notifications_router, _social_router, _oauth_router,
):
    app.include_router(r.router)


# -----------------------------------------------------------------------------
# STARTUP — legacy→layered migration + seed default View/Clip promos
# -----------------------------------------------------------------------------
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
    # 1. One-shot migration from the legacy single-DB to the 3-layer architecture.
    migrated = 0
    for coll_name, layer in _COLLECTION_LAYER.items():
        target = _LAYER_DB[layer]
        # If the legacy DB IS the target layer, nothing to migrate.
        if _LEGACY_DB_NAME in {_IDENTITY_DB_NAME, _STREAMING_DB_NAME, _VAULT_DB_NAME}:
            continue
        try:
            if await target[coll_name].estimated_document_count() > 0:
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

    # 2. Seed the default View/Clip self-promos the very first time.
    try:
        if await db.content.count_documents({"is_promo": True}) == 0:
            for p in _DEFAULT_PROMOS:
                await db.content.insert_one({
                    "id": str(uuid.uuid4()),
                    **p,
                    "type": "promo",
                    "duration": 30,
                    "is_promo": True,
                    "views": 0,
                    "created_at": now_iso(),
                })
            logger.info("Seeded default View/Clip self-promos")
    except Exception as e:
        logger.warning(f"Promo seed skipped: {e}")

    logger.info(
        f"View/Clip v{os.environ.get('APP_VERSION', '1.4.0')} ready | "
        f"DBs: identity={_IDENTITY_DB_NAME} streaming={_STREAMING_DB_NAME} vault={_VAULT_DB_NAME}"
    )
    logger.info(
        "Integrations — Stripe: %s | Live Stream: %s",
        "REAL" if stripe_service.real_stripe_enabled()
        else "MOCK (set STRIPE_API_KEY to real sk_test_/sk_live_ key to activate)",
        "REAL (GCP)" if live_stream_service.is_live_enabled()
        else "MOCK (set GOOGLE_CLOUD_PROJECT + LIVESTREAM_GCS_BUCKET + "
             "GOOGLE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS to activate)",
    )


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
