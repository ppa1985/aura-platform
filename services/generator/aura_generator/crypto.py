"""Symmetric encryption for user-provided secrets (e.g. git PATs)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from .config import settings


def _fernet() -> Fernet:
    key = settings.encryption_key
    # Accept either a valid 32-byte urlsafe base64 key or any string we'll hash.
    try:
        raw = base64.urlsafe_b64decode(key)
        if len(raw) == 32:
            return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        pass
    digest = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
