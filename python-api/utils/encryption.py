"""
Encryption utilities for securing integration secrets.

Uses Fernet symmetric encryption backed by ENCRYPTION_MASTER_KEY.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from config import settings

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet() -> Fernet:
    """Return a cached Fernet instance, creating one if needed."""
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_MASTER_KEY
        if not key:
            key = Fernet.generate_key().decode()
            logger.warning(
                "ENCRYPTION_MASTER_KEY not set, using auto-generated key "
                "(data will not survive restarts)"
            )
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return the ciphertext as a string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a ciphertext string and return the original plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
