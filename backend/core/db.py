"""Triple-layer enterprise MongoDB architecture.

Three logical databases on the shared cluster:
  1. IDENTITY_DB  — account credentials, subscriptions, settings
  2. STREAMING_DB — live stream data, content, chat, follows, notifications
  3. VAULT_DB     — payments, gifts, earnings, payouts, banking info (encrypted)
Each DB can be migrated to its own physical cluster by changing env vars only.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient

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
    """Transparently routes `db.users`, `db.gifts`, etc. to the appropriate logical DB."""
    def __getattr__(self, name: str):
        layer = _COLLECTION_LAYER.get(name, 'identity')
        return _LAYER_DB[layer][name]


db = DBRouter()
