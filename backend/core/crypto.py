"""Vault field-level encryption — Fernet (AES-128-CBC + HMAC-SHA256).

The active cipher is mutable at module-level so the admin key-rotation worker
can swap it in-process. Callers must use `vault_encrypt`/`vault_decrypt`, NOT
the cipher object directly, so rotations take effect immediately.
"""
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

_VAULT_KEY = os.environ.get('VAULT_ENCRYPTION_KEY')
if not _VAULT_KEY:
    # Auto-generate on first boot. In production this MUST come from env.
    _VAULT_KEY = Fernet.generate_key().decode()
    logging.warning("VAULT_ENCRYPTION_KEY missing — generated ephemeral key (dev only)")

_vault_cipher = Fernet(_VAULT_KEY.encode() if isinstance(_VAULT_KEY, str) else _VAULT_KEY)


def vault_encrypt(plaintext: Optional[str]) -> Optional[str]:
    if plaintext is None:
        return None
    return _vault_cipher.encrypt(plaintext.encode()).decode()


def vault_decrypt(ciphertext: Optional[str]) -> Optional[str]:
    if not ciphertext:
        return None
    try:
        return _vault_cipher.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None


def mask_bank(plaintext: Optional[str]) -> str:
    """Last-4 masking for display."""
    if not plaintext:
        return ""
    tail = plaintext[-4:]
    return f"•••• {tail}"


def current_cipher() -> Fernet:
    """Accessor used by the rotate-keys worker — returns the active cipher."""
    return _vault_cipher


def replace_cipher(new_key: str) -> None:
    """Called by the rotate-keys worker after re-encrypting all records with
    a new Fernet key. Swaps the active cipher in-process."""
    global _vault_cipher, _VAULT_KEY
    _vault_cipher = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)
    _VAULT_KEY = new_key


def vault_key_configured() -> bool:
    return bool(_VAULT_KEY)
