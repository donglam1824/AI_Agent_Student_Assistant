"""
services/microsoft_oauth_service.py
-----------------------------------
Microsoft delegated OAuth helpers for Graph access per user.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import msal
import requests
from sqlalchemy.orm import Session

from config.settings import settings
from core.crypto import decrypt_token
from core.logger import logger
from db import crud


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


def _tenant() -> str:
    return settings.azure_tenant_id or "common"


def _authority() -> str:
    return f"https://login.microsoftonline.com/{_tenant()}"


def get_microsoft_scopes() -> list[str]:
    return [scope for scope in settings.microsoft_scopes.split(" ") if scope.strip()]


def build_authorization_url(redirect_uri: Optional[str] = None, state: Optional[str] = None) -> str:
    if not settings.azure_client_id:
        raise ValueError("MS_CLIENT_ID/AZURE_CLIENT_ID is not configured.")

    params = {
        "client_id": settings.azure_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri or settings.microsoft_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(get_microsoft_scopes()),
        "prompt": "select_account",
    }
    if state:
        params["state"] = state
    return f"{_authority()}/oauth2/v2.0/authorize?{urlencode(params)}"


def _confidential_app() -> msal.ConfidentialClientApplication:
    if not settings.azure_client_id or not settings.azure_client_secret:
        raise ValueError("MS_CLIENT_ID/MS_CLIENT_SECRET are not configured.")
    return msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=_authority(),
    )


def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    result = _confidential_app().acquire_token_by_authorization_code(
        code=code,
        scopes=get_microsoft_scopes(),
        redirect_uri=redirect_uri,
    )
    if "access_token" not in result:
        raise ValueError(result.get("error_description") or "Microsoft token exchange failed.")
    return result


def refresh_microsoft_tokens(refresh_token: str) -> dict:
    result = _confidential_app().acquire_token_by_refresh_token(
        refresh_token=refresh_token,
        scopes=get_microsoft_scopes(),
    )
    if "access_token" not in result:
        raise ValueError(result.get("error_description") or "Microsoft token refresh failed.")
    return result


def get_graph_profile(access_token: str) -> dict:
    response = requests.get(
        f"{GRAPH_ROOT}/me",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def save_microsoft_tokens(db: Session, user_id: str, token_result: dict) -> None:
    access_token = token_result["access_token"]
    refresh_token = token_result.get("refresh_token")
    expires_in = int(token_result.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 120, 60))

    profile = get_graph_profile(access_token)
    account_email = profile.get("mail") or profile.get("userPrincipalName")

    crud.update_user_microsoft_tokens(
        db=db,
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        account_email=account_email,
    )


def get_user_microsoft_access_token(db: Session, user_id: str) -> str:
    user = crud.get_user_by_id(db, user_id)
    if not user or not user.microsoft_access_token:
        raise ValueError("User has not connected a Microsoft account.")

    access_token = decrypt_token(user.microsoft_access_token)
    refresh_token = decrypt_token(user.microsoft_refresh_token)
    expires_at = user.microsoft_token_expires_at

    now = datetime.now(timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if refresh_token and (not expires_at or expires_at <= now):
        logger.info(f"[Microsoft OAuth] Refreshing token for user={user_id}")
        result = refresh_microsoft_tokens(refresh_token)
        save_microsoft_tokens(db, user_id, result)
        access_token = result["access_token"]

    return access_token
