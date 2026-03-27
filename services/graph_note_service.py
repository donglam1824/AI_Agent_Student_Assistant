"""
services/graph_note_service.py
---------------------------------
Abstraction over Note API.
"""

from __future__ import annotations
import uuid
import datetime
from abc import ABC, abstractmethod
from typing import List

from models.note import NoteItem, NoteCreate, NoteUpdate
from core.logger import logger


class BaseNoteService(ABC):
    @abstractmethod
    async def list_notes(self, limit: int = 5) -> List[NoteItem]: ...

    @abstractmethod
    async def create_note(self, data: NoteCreate) -> NoteItem: ...


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
                created_at="2026-03-26T10:00:00Z"
            )
        )

    async def list_notes(self, limit: int = 5) -> List[NoteItem]:
        logger.debug(f"[Mock Note] Listing notes: limit={limit}")
        return self._store[:limit]

    async def create_note(self, data: NoteCreate) -> NoteItem:
        logger.info(f"[Mock Note] Created note '{data.title}'")
        note = NoteItem(
            id=str(uuid.uuid4()),
            title=data.title,
            content=data.content,
            created_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
        self._store.append(note)
        return note


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
                    created_at=p.created_date_time.isoformat() if p.created_date_time else ""
                ))
        return notes

    async def create_note(self, data: NoteCreate) -> NoteItem:
        # For simplicity, returning mock response if not implemented fully for Graph html page creations
        logger.warning("GraphNoteService create_note not fully implemented for OneNote HTML yet")
        return await MockNoteService().create_note(data)


def get_note_service() -> BaseNoteService:
    from config.settings import settings
    provider = settings.note_provider.lower().strip()

    if provider == "mock" or settings.mock_graph:
        return MockNoteService()

    if provider == "google":
        from services.google_note_service import GoogleNoteService
        return GoogleNoteService()

    if provider == "msgraph":
        return GraphNoteService()

    raise ValueError(f"Unknown NOTE_PROVIDER={provider!r}")
