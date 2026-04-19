"""View/Clip economic constants and default platform settings."""
from typing import Any, Dict, List

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

DEFAULT_SETTINGS: Dict[str, Any] = {
    "viewer_sub_price": VIEWER_SUB_PRICE,
    "streamer_sub_price": STREAMER_SUB_PRICE,
    "earnings_per_view": 0.005,             # $0.005 per qualified 30-min view
    "view_threshold_minutes": 30,
    "earnings_per_100k_views": 5.00,
    "gift_base_rate": 0.002,
    "budget_alert_percent": 80,             # admin-configurable bandwidth cap %
    "maintenance_mode": False,
}
