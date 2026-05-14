"""
api/v1/auth.py
--------------
Authentication endpoints:
  - POST /auth/google  → Exchange Google authorization_code, create/update user, return JWT
  - GET  /auth/me      → Get current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import User
from core.security import create_access_token
from core.logger import logger
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request / Response Models ─────────────────────────────────────────────

class GoogleLoginRequest(BaseModel):
    code: str           # authorization_code từ Frontend (Google OAuth2 code flow)
    redirect_uri: str   # phải khớp với redirect_uri đã dùng ở phía frontend


class MicrosoftLoginRequest(BaseModel):
    code: str
    redirect_uri: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    picture: str | None


class ConnectionStatusResponse(BaseModel):
    google_connected: bool
    microsoft_connected: bool
    microsoft_account_email: str | None = None


class MicrosoftAuthUrlResponse(BaseModel):
    auth_url: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/google", response_model=AuthResponse)
async def login_with_google(
    body: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Nhận authorization_code từ Frontend sau khi user đồng ý cấp quyền Google.
    Backend trao đổi code lấy access_token + refresh_token, lưu vào DB mã hóa,
    rồi trả về JWT của ứng dụng ORCA.
    """
    from config.settings import settings
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    from google_auth_oauthlib.flow import Flow

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID hoặc GOOGLE_CLIENT_SECRET chưa được cấu hình trên server.",
        )

    # Nới lỏng kiểm tra scope để tránh lỗi "Scope has changed" từ oauthlib
    import os
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

    # Trao đổi authorization_code lấy tokens
    try:
        client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [body.redirect_uri],
            }
        }

        scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/tasks",
            "https://www.googleapis.com/auth/drive.readonly",  # Google Drive RAG
        ]

        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri=body.redirect_uri,
        )
        flow.fetch_token(code=body.code)
        credentials = flow.credentials

    except Exception as e:
        logger.error(f"[auth] Google token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Không thể trao đổi authorization code với Google: {str(e)}",
        )

    # Lấy thông tin user từ id_token
    try:
        idinfo = google_id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as e:
        logger.error(f"[auth] id_token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác minh thông tin người dùng từ Google.",
        )

    email = idinfo.get("email")
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy email trong token.",
        )

    # Lưu user + tokens mã hóa vào DB
    user = crud.create_or_update_user(
        db=db,
        email=email,
        name=name,
        picture=picture,
        google_access_token=credentials.token,
        google_refresh_token=credentials.refresh_token,
    )

    logger.info(f"[auth] Login success: {email} (user_id={user.id})")

    # Phát hành JWT nội bộ
    jwt_token = create_access_token(user_id=user.id, email=user.email)

    return AuthResponse(
        access_token=jwt_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
    )


@router.get("/connections", response_model=ConnectionStatusResponse)
async def get_connections(current_user: User = Depends(get_current_user)):
    """Return connected external accounts for the current user."""
    return ConnectionStatusResponse(
        google_connected=bool(current_user.google_access_token or current_user.google_refresh_token),
        microsoft_connected=bool(current_user.microsoft_access_token or current_user.microsoft_refresh_token),
        microsoft_account_email=current_user.microsoft_account_email,
    )


@router.get("/microsoft/url", response_model=MicrosoftAuthUrlResponse)
async def get_microsoft_auth_url(
    redirect_uri: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """Build a Microsoft authorization URL for connecting the current user."""
    _ = current_user
    try:
        from services.microsoft_oauth_service import build_authorization_url

        return MicrosoftAuthUrlResponse(auth_url=build_authorization_url(redirect_uri=redirect_uri))
    except Exception as e:
        logger.error(f"[auth] Microsoft auth URL failed: {e}")
        raise HTTPException(status_code=500, detail=f"Khong the tao URL dang nhap Microsoft: {str(e)}")


@router.post("/microsoft")
async def connect_microsoft(
    body: MicrosoftLoginRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange Microsoft authorization_code and store encrypted tokens for current user."""
    try:
        from services.microsoft_oauth_service import exchange_code_for_tokens, save_microsoft_tokens

        result = exchange_code_for_tokens(code=body.code, redirect_uri=body.redirect_uri)
        save_microsoft_tokens(db=db, user_id=current_user.id, token_result=result)
        user = crud.get_user_by_id(db, current_user.id)
        return {
            "message": "Đã kết nối Microsoft thành công.",
            "microsoft_account_email": user.microsoft_account_email if user else None,
        }
    except Exception as e:
        logger.error(f"[auth] Microsoft connect failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Không thể kế nối tới Microsoft: {str(e)}",
        )


@router.delete("/microsoft")
async def disconnect_microsoft(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect Microsoft account for current user."""
    crud.disconnect_user_microsoft(db, current_user.id)
    return {"message": "Da ngat ket noi Microsoft."}
