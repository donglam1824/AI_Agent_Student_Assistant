"""
services/google_note_service.py
---------------------------------
Google Keep (via Google Keep API) implementation – multi-tenant, token từ Database.

Lưu ý: Google Keep API hiện đang ở dạng Limited Access (chỉ dành cho workspace apps).
Trong phạm vi dự án học tập, chúng ta dùng Google Tasks API như một giải pháp thay thế,
vì Google Keep API chưa public cho personal accounts.

Scope cần:
  - https://www.googleapis.com/auth/tasks
"""

from __future__ import annotations
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.logger import logger
from services.base_note_service import BaseNoteService
from models.note import NoteItem


SCOPES = ["https://www.googleapis.com/auth/tasks"]
DEFAULT_TASKLIST = "@default"


def _get_credentials_from_db(user_id: str) -> Credentials:
    """Truy vấn DB lấy token đã mã hóa, giải mã và tạo Credentials cho Google Tasks."""
    from db.database import SessionLocal
    from db import crud
    from core.crypto import decrypt_token
    from config.settings import settings

    db = SessionLocal()
    try:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise ValueError(f"User {user_id} không tồn tại trong DB.")

        access_token = decrypt_token(user.google_access_token)
        refresh_token = decrypt_token(user.google_refresh_token)

        if not access_token and not refresh_token:
            raise ValueError(
                f"User {user_id} chưa có Google token. Vui lòng đăng nhập lại."
            )

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=SCOPES,
        )

        if not creds.valid and creds.refresh_token:
            logger.info(f"[Google Tasks] Refreshing token for user={user_id}")
            creds.refresh(Request())
            crud.update_user_tokens(
                db=db,
                user_id=user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
            )

        return creds
    finally:
        db.close()


class GoogleNoteService(BaseNoteService):
    """
    Ghi chú qua Google Tasks API.
    Mỗi ghi chú = 1 Task trong Default Tasklist của user.
    Title → task.title, Content → task.notes
    """

    def __init__(self, user_id: str) -> None:
        creds = _get_credentials_from_db(user_id)
        self._service = build("tasks", "v1", credentials=creds)
        self._user_id = user_id
        logger.info(f"[Google Tasks] Service ready for user={user_id}")

    def _get_or_create_orca_tasklist(self) -> str:
        """Lấy hoặc tạo Tasklist tên 'ORCA Notes' để ghi chú tách biệt."""
        try:
            result = self._service.tasklists().list().execute()
            for tl in result.get("items", []):
                if tl.get("title") == "ORCA Notes":
                    return tl["id"]
            # Tạo mới nếu chưa có
            new_tl = self._service.tasklists().insert(body={"title": "ORCA Notes"}).execute()
            logger.info(f"[Google Tasks] Created 'ORCA Notes' tasklist: {new_tl['id']}")
            return new_tl["id"]
        except HttpError as e:
            logger.warning(f"[Google Tasks] Cannot get tasklist, using @default: {e}")
            return DEFAULT_TASKLIST

    def _map_task_to_note(self, task: dict) -> NoteItem:
        updated = task.get("updated", "")
        return NoteItem(
            id=task.get("id", ""),
            title=task.get("title", ""),
            content=task.get("notes", ""),
            created_at=updated,
            updated_at=updated
        )

    async def list_notes(self, limit: int = 20) -> List[NoteItem]:
        """Lấy danh sách ghi chú (tasks) từ ORCA Notes tasklist."""
        tasklist_id = self._get_or_create_orca_tasklist()
        try:
            result = self._service.tasks().list(
                tasklist=tasklist_id,
                maxResults=limit,
                showCompleted=False,
            ).execute()
            tasks = result.get("items", [])
            return [self._map_task_to_note(t) for t in tasks]
        except HttpError as e:
            logger.error(f"[Google Tasks] list_notes error: {e}")
            raise

    async def create_note(self, title: str, content: str = "") -> NoteItem:
        """Tạo ghi chú mới (task) trong ORCA Notes."""
        tasklist_id = self._get_or_create_orca_tasklist()
        task_body = {
            "title": title,
            "notes": content,
        }
        try:
            created = self._service.tasks().insert(
                tasklist=tasklist_id,
                body=task_body,
            ).execute()
            logger.info(f"[Google Tasks] user={self._user_id} created note: {created.get('id')}")
            return self._map_task_to_note(created)
        except HttpError as e:
            logger.error(f"[Google Tasks] create_note error: {e}")
            raise

    async def update_note(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None) -> NoteItem:
        """Sửa ghi chú."""
        tasklist_id = self._get_or_create_orca_tasklist()
        task_body = {}
        if title is not None:
            task_body["title"] = title
        if content is not None:
            task_body["notes"] = content

        try:
            updated = self._service.tasks().patch(
                tasklist=tasklist_id,
                task=note_id,
                body=task_body,
            ).execute()
            logger.info(f"[Google Tasks] user={self._user_id} updated note: {note_id}")
            return self._map_task_to_note(updated)
        except HttpError as e:
            logger.error(f"[Google Tasks] update_note error: {e}")
            raise

    async def delete_note(self, note_id: str) -> bool:
        """Xóa ghi chú (đánh dấu task hoàn thành / xóa)."""
        tasklist_id = self._get_or_create_orca_tasklist()
        try:
            self._service.tasks().delete(tasklist=tasklist_id, task=note_id).execute()
            logger.info(f"[Google Tasks] user={self._user_id} deleted note: {note_id}")
            return True
        except HttpError as e:
            logger.error(f"[Google Tasks] delete_note error: {e}")
            return False
