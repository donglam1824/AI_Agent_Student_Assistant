"""
api/v1/auth.py
--------------
Authentication endpoints:
  - POST /auth/google  → Verify Google ID token, create/update user, return JWT
  - GET  /auth/me      → Get current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from db.database import get_db
from db import crud
from db.models import User
from core.security import create_access_token
from api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request / Response Models ─────────────────────────────────────────────

class GoogleLoginRequest(BaseModel):
    id_token: str
    access_token: str | None = None
    refresh_token: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    picture: str | None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/google", response_model=AuthResponse)
async def login_with_google(
    body: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Verify a Google ID token and issue a JWT for the ORCA API.
    Frontend sends the id_token obtained from NextAuth/Google OAuth.
    """
    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token không hợp lệ.",
        )

    email = idinfo.get("email")
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy email trong token.",
        )

    # Create or update user in DB
    user = crud.create_or_update_user(
        db=db,
        email=email,
        name=name,
        picture=picture,
        google_access_token=body.access_token,
        google_refresh_token=body.refresh_token,
    )

    # Issue JWT
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
