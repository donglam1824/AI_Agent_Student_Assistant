"""
Tạo và xác thực JWT token.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from config.settings import settings

JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_EXPIRE_HOURS = 24 * 7  # 7 days
JWT_REFRESH_GRACE_HOURS = 24


class TokenData(BaseModel):
    user_id: str
    email: str


def create_access_token(user_id: str, email: str) -> str:
    """Tạo JWT access token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[TokenData]:
    """Xác thực và giải mã JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            return None
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None

def decode_token_allow_expired(token: str) -> Optional[TokenData]:
    """Giải mã JWT token, chấp nhận hết hạn trong khoảng gia hạn (grace period)"""
    try:
        # Bỏ qua tự động check exp
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        
        # Kiểm tra exp thủ công kèm thời gian gia hạn
        exp = payload.get("exp")
        if exp is not None:
            exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            grace_period = timedelta(hours=JWT_REFRESH_GRACE_HOURS)
            if datetime.now(timezone.utc) > exp_time + grace_period:
                return None # Đã quá thời gian gia hạn
                
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            return None
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None
