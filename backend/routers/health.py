"""Public liveness + readiness probes. No auth, no admin scope."""
import asyncio
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.db import db_identity, db_streaming, db_vault

router = APIRouter(prefix="/api")


@router.get("/health")
async def public_health():
    """Liveness probe — green if the process is up."""
    return {"status": "ok", "version": os.environ.get("APP_VERSION", "1.4.0")}


@router.get("/ready")
async def public_ready():
    """Readiness probe — 503 if any DB layer fails to respond."""
    async def ping(dbh):
        try:
            await dbh.command("ping")
            return True
        except Exception:
            return False
    oks = await asyncio.gather(ping(db_identity), ping(db_streaming), ping(db_vault))
    if not all(oks):
        return JSONResponse(
            status_code=503,
            content={"status": "degraded",
                     "identity": oks[0], "streaming": oks[1], "vault": oks[2]},
        )
    return {"status": "ready"}
