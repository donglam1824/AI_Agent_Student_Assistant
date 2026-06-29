"""
services/graph_note_service.py
---------------------------------
Abstraction over Note API for Microsoft Graph.
"""

from __future__ import annotations
import uuid
import datetime
from typing import List, Optional

from models.note import NoteItem
from services.base_note_service import BaseNoteService
from core.logger import logger

class MockNoteService(BaseNoteService):
    def __init__(self) -> None:
        self._store: list[NoteItem] = []
        self._seed()

    def _seed(self) -> None:
        self._store.append(
            NoteItem(
                id=str(uuid.uuid4()),
                title="Ghi chú môn AI",
                content="Cần làm bài tập lớn về LangGraph.",
                created_at="2026-03-26T10:00:00Z",
                updated_at="2026-03-26T10:00:00Z"
            )
        )

    async def list_notes(self, limit: int = 5) -> List[NoteItem]:
        logger.debug(f"[Mock Note] Listing notes: limit={limit}")
        return self._store[:limit]

    async def create_note(self, title: str, content: str = "") -> NoteItem:
        logger.info(f"[Mock Note] Created note '{title}'")
        now = datetime.datetime.utcnow().isoformat() + "Z"
        note = NoteItem(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            created_at=now,
            updated_at=now
        )
        self._store.append(note)
        return note

    async def update_note(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None) -> NoteItem:
        for note in self._store:
            if note.id == note_id:
                if title is not None:
                    note.title = title
                if content is not None:
                    note.content = content
                note.updated_at = datetime.datetime.utcnow().isoformat() + "Z"
                return note
        raise ValueError(f"Note {note_id} not found")

    async def delete_note(self, note_id: str) -> bool:
        for idx, note in enumerate(self._store):
            if note.id == note_id:
                self._store.pop(idx)
                return True
        return False


class GraphNoteService(BaseNoteService):
    """Real implementation using Microsoft Graph SDK for OneNote."""
    def __init__(self) -> None:
        from core.auth import get_graph_client
        from config.settings import settings
        self._client = get_graph_client()
        self._user_id = settings.graph_user_id

    async def list_notes(self, limit: int = 5) -> List[NoteItem]:
        logger.info(f"[Graph Note] Fetching {limit} notes")
        result = await (
            self._client.users
            .by_user_id(self._user_id)
            .onenote
            .pages
            .get(request_configuration=lambda cfg: setattr(
                cfg.query_parameters, "top", limit
            ))
        )
        notes = []
        if result and result.value:
            for p in result.value:
                notes.append(NoteItem(
                    id=p.id or "",
                    title=p.title or "(Không có tiêu đề)",
                    content="[Nội dung OneNote cần được tải riêng thông qua content endpoint]",
                    created_at=p.created_date_time.isoformat() if p.created_date_time else "",
                    updated_at=p.created_date_time.isoformat() if p.created_date_time else ""
                ))
        return notes

    async def create_note(self, title: str, content: str = "") -> NoteItem:
        # For simplicity, returning mock response if not implemented fully for Graph html page creations
        logger.warning("GraphNoteService create_note not fully implemented for OneNote HTML yet")
        return await MockNoteService().create_note(title=title, content=content)

    async def update_note(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None) -> NoteItem:
        logger.warning("GraphNoteService update_note not fully implemented for OneNote HTML yet")
        raise NotImplementedError()

    async def delete_note(self, note_id: str) -> bool:
        logger.warning("GraphNoteService delete_note not fully implemented for OneNote HTML yet")
        raise NotImplementedError()
