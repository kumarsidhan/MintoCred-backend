"""
AES-256-GCM encryption for sensitive fields like PAN number.
Each value is encrypted with a unique random nonce — same PAN
encrypted twice will produce different ciphertext (non-deterministic).
"""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def _get_key() -> bytes:
    """Derive a 32-byte AES key from the JWT secret (first 32 bytes of hex-decoded)."""
    raw = settings.JWT_SECRET_KEY.encode("utf-8")
    # Pad or truncate to exactly 32 bytes
    return (raw * 2)[:32]


def encrypt_pan(plain_pan: str) -> str:
    """
    Encrypt PAN using AES-256-GCM.
    Returns base64(nonce + ciphertext) as a string safe for DB storage.
    """
    key   = _get_key()
    aesgcm = AESGCM(key)
    nonce  = os.urandom(12)   # 96-bit nonce — unique per encryption
    ct     = aesgcm.encrypt(nonce, plain_pan.upper().encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def decrypt_pan(encrypted: str) -> str:
    """
    Decrypt a PAN value previously encrypted with encrypt_pan().
    Returns the original plain-text PAN string.
    """
    key    = _get_key()
    aesgcm = AESGCM(key)
    raw    = base64.b64decode(encrypted.encode("utf-8"))
    nonce  = raw[:12]
    ct     = raw[12:]
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


def mask_pan(plain_pan: str) -> str:
    """
    Return masked PAN for display: ABCDE1234F → ABCDE****F
    Never return plain PAN in API responses.
    """
    if len(plain_pan) != 10:
        return "**********"
    return plain_pan[:5] + "****" + plain_pan[-1]
