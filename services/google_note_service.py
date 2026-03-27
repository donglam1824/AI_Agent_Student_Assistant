"""
services/google_note_service.py
---------------------------------
Google Note (Tasks API mapped to Notes) implementation.
"""

from __future__ import annotations
import os
import datetime
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.note import NoteItem, NoteCreate, NoteUpdate
from services.graph_note_service import BaseNoteService
from core.logger import logger

SCOPES = ["https://www.googleapis.com/auth/tasks"]

def _get_credentials(credentials_path: str, token_path: str) -> Credentials:
    creds: Credentials | None = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("[Google Note] Refreshing expired token...")
            creds.refresh(Request())
        else:
            logger.info("[Google Note] No valid token. Starting OAuth2 flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            try:
                creds = flow.run_local_server(port=0, timeout_seconds=15)
            except Exception as e:
                logger.warning(f"[Google Note] Local server failed ({e}). Falling back to manual auth.")
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                auth_url, _ = flow.authorization_url(prompt='consent')
                print("\n" + "="*60)
                print("⚠️ GOOGLE TASKS AUTH: KHÔNG THỂ TỰ ĐỘNG BẮT MÃ XÁC THỰC ⚠️")
                print("1. Hãy mở đường link sau trong trình duyệt:")
                print(auth_url)
                code = input("\n2. Nhập mã code bạn nhận được từ Google: ").strip()
                print("="*60 + "\n")
                flow.fetch_token(code=code)
                creds = flow.credentials

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info(f"[Google Note] Token saved to {token_path}")
    return creds


class GoogleNoteService(BaseNoteService):
    def __init__(self) -> None:
        from config.settings import settings
        creds = _get_credentials(
            credentials_path=settings.google_credentials_path,
            token_path=settings.google_token_note_path,
        )
        self._service = build("tasks", "v1", credentials=creds)
        logger.info("[Google Note] Tasks mapped to Note service ready.")

    async def list_notes(self, limit: int = 5) -> List[NoteItem]:
        logger.info(f"[Google Note] Fetching {limit} notes")
        try:
            results = self._service.tasks().list(tasklist='@default', maxResults=limit).execute()
            items = results.get('items', [])
            note_list = []
            
            for task in items:
                note_list.append(NoteItem(
                    id=task.get('id', ''),
                    title=task.get('title', '(Không có tiêu đề)'),
                    content=task.get('notes', ''),
                    created_at=task.get('updated', '') 
                ))
            return note_list
        except HttpError as error:
            logger.error(f"[Google Note] list_notes error: {error}")
            raise

    async def create_note(self, data: NoteCreate) -> NoteItem:
        logger.info(f"[Google Note] Creating note: {data.title}")
        task_body = {
            'title': data.title,
            'notes': data.content
        }
        try:
            task = self._service.tasks().insert(tasklist='@default', body=task_body).execute()
            return NoteItem(
                id=task.get('id', ''),
                title=task.get('title', ''),
                content=task.get('notes', ''),
                created_at=task.get('updated', '')
            )
        except HttpError as error:
            logger.error(f"[Google Note] create_note error: {error}")
            raise
