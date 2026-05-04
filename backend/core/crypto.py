"""
core/crypto.py
--------------
Mã hóa / giải mã token Google lưu trong Database.
Dùng Fernet (AES-128-CBC + HMAC) từ thư viện `cryptography`.

Cách dùng:
    from core.crypto import encrypt_token, decrypt_token

    enc = encrypt_token("ya29.access_token_here")
    dec = decrypt_token(enc)   # → "ya29.access_token_here"
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from config.settings import settings
from core.logger import logger


def _get_fernet() -> Fernet:
    """Tạo Fernet instance từ TOKEN_ENCRYPTION_KEY trong .env."""
    key = settings.token_encryption_key
    if not key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY chưa được cấu hình trong .env!\n"
            "Tạo key mới bằng lệnh: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    # Đảm bảo key đúng format Fernet (base64, 32 bytes)
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise RuntimeError(f"TOKEN_ENCRYPTION_KEY không hợp lệ: {e}")


def encrypt_token(plain_token: Optional[str]) -> Optional[str]:
    """
    Mã hóa token thành chuỗi base64 an toàn để lưu DB.
    Trả về None nếu plain_token là None hoặc rỗng.
    """
    if not plain_token:
        return None
    try:
        f = _get_fernet()
        return f.encrypt(plain_token.encode()).decode()
    except Exception as e:
        logger.error(f"[crypto] encrypt_token failed: {e}")
        raise


def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """
    Giải mã token đã được mã hóa từ DB.
    Trả về None nếu encrypted_token là None hoặc giải mã thất bại.
    """
    if not encrypted_token:
        return None
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        logger.warning("[crypto] decrypt_token: InvalidToken – token bị sai hoặc key thay đổi.")
        return None
    except Exception as e:
        logger.error(f"[crypto] decrypt_token failed: {e}")
        return None
