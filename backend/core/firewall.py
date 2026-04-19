"""Level-3 logic firewall — per-IP rate limit, admin IP allowlist, request counters.

State lives at module level so the admin /system/health endpoint can read counts,
and FirewallMiddleware can mutate them. Do not instantiate; import globals directly.
"""
import logging
import os
import uuid
from collections import defaultdict, deque
from ipaddress import ip_address, ip_network
from typing import Dict

from core.db import db
from core.helpers import now_iso

logger = logging.getLogger(__name__)

_RATE_WINDOW_SEC = 60
_RATE_LIMIT = int(os.environ.get("FIREWALL_RATE_LIMIT_PER_MIN", "300"))
_ip_hits: Dict[str, deque] = defaultdict(deque)
_REQUEST_COUNTER = {"total": 0, "by_path": defaultdict(int)}


def _parse_allowlist(raw: str):
    nets = []
    for item in (raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            nets.append(ip_network(item, strict=False))
        except ValueError:
            try:
                nets.append(ip_network(f"{item}/32", strict=False))
            except ValueError:
                logger.warning("ADMIN_IP_ALLOWLIST: skipping invalid entry %s", item)
    return nets


_ADMIN_ALLOWLIST_NETS = _parse_allowlist(os.environ.get("ADMIN_IP_ALLOWLIST", ""))


def ip_allowed_for_admin(ip: str) -> bool:
    if not _ADMIN_ALLOWLIST_NETS:
        return True
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    return any(addr in n for n in _ADMIN_ALLOWLIST_NETS)


async def audit_blocked_admin_ip(ip: str, path: str) -> None:
    try:
        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "actor_id": None,
            "action": "admin.ip.blocked",
            "meta": {"ip": ip, "path": path},
            "created_at": now_iso(),
        })
    except Exception:
        pass
