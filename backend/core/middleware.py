"""FirewallMiddleware + RequestIDMiddleware. Mounted in server.py."""
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core import firewall as fw


class FirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        ip = request.client.host if request.client else "unknown"
        now = time.time()

        # IP allowlist for admin surfaces (login + admin API)
        if (path.startswith("/api/admin/") or path == "/api/admin/auth/login") \
                and not fw.ip_allowed_for_admin(ip):
            fw._REQUEST_COUNTER["blocked"] = fw._REQUEST_COUNTER.get("blocked", 0) + 1
            await fw.audit_blocked_admin_ip(ip, path)
            return JSONResponse(status_code=403, content={"detail": "IP not allowed"})

        # Sliding-window rate limit for any /api/*
        if path.startswith("/api/"):
            q = fw._ip_hits[ip]
            while q and now - q[0] > fw._RATE_WINDOW_SEC:
                q.popleft()
            if len(q) >= fw._RATE_LIMIT:
                fw._REQUEST_COUNTER["blocked"] = fw._REQUEST_COUNTER.get("blocked", 0) + 1
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            q.append(now)
            fw._REQUEST_COUNTER["total"] += 1
            fw._REQUEST_COUNTER["by_path"][path] += 1

        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Echoes incoming X-Request-ID header or generates a UUID4 per request."""
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
