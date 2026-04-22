"""
services/graph_calendar_service.py
-----------------------------------
Abstraction over Microsoft Graph Calendar API.

Two implementations:
  - GraphCalendarService  → real Microsoft Graph calls (async)
  - MockCalendarService   → in-memory fake for local dev/testing

The agent/tools layer should only depend on the abstract interface.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import List

from models.calendar import CalendarEvent, DateTimeTimeZone, EventCreate, EventUpdate
from core.logger import logger


# ─────────────────────────────────────────────────────────────────────────────
# Abstract interface
# ─────────────────────────────────────────────────────────────────────────────

class BaseCalendarService(ABC):
    @abstractmethod
    async def list_events(self, start: datetime, end: datetime) -> List[CalendarEvent]: ...

    @abstractmethod
    async def create_event(self, data: EventCreate) -> CalendarEvent: ...

    @abstractmethod
    async def update_event(self, event_id: str, data: EventUpdate) -> CalendarEvent: ...

    @abstractmethod
    async def delete_event(self, event_id: str) -> bool: ...


# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation (no credentials needed)
# ─────────────────────────────────────────────────────────────────────────────

class MockCalendarService(BaseCalendarService):
    """In-memory calendar service for development and testing."""

    def __init__(self) -> None:
        self._store: dict[str, CalendarEvent] = {}
        # Seed a couple of fake events
        self._seed()

    def _seed(self) -> None:
        now = datetime.now(timezone.utc)
        seed_subjects = [
            "L\u1ecbch h\u1ecdc To\u00e1n",
            "N\u1ed9p b\u00e0i t\u1eadp l\u1edbn",
            "H\u1eafp nh\u00f3m d\u1ef1 \u00e1n",
        ]
        for i, subject in enumerate(seed_subjects):
            start = now + timedelta(days=i + 1, hours=8)
            end = start + timedelta(hours=1, minutes=30)
            evt = CalendarEvent(
                id=str(uuid.uuid4()),
                subject=subject,
                start=DateTimeTimeZone(dateTime=start.strftime("%Y-%m-%dT%H:%M:%S")),
                end=DateTimeTimeZone(dateTime=end.strftime("%Y-%m-%dT%H:%M:%S")),
                body=f"Chi tiết sự kiện '{subject}'",
                location="Phòng 301",
                created_at=now,
            )
            self._store[evt.id] = evt

    async def list_events(self, start: datetime, end: datetime) -> List[CalendarEvent]:
        logger.debug(f"[Mock] Listing events from {start} to {end}")
        return list(self._store.values())

    async def create_event(self, data: EventCreate) -> CalendarEvent:
        logger.debug(f"[Mock] Creating event: {data.subject}")
        evt = CalendarEvent(
            id=str(uuid.uuid4()),
            subject=data.subject,
            start=data.start,
            end=data.end,
            body=data.body,
            location=data.location,
            is_online_meeting=data.is_online_meeting,
            created_at=datetime.now(timezone.utc),
        )
        self._store[evt.id] = evt
        logger.info(f"[Mock] Event created: {evt.id} – {evt.subject}")
        return evt

    async def update_event(self, event_id: str, data: EventUpdate) -> CalendarEvent:
        logger.debug(f"[Mock] Updating event: {event_id}")
        if event_id not in self._store:
            raise ValueError(f"Event {event_id} not found.")
        evt = self._store[event_id]
        update_data = data.model_dump(exclude_none=True)
        updated = evt.model_copy(update=update_data)
        self._store[event_id] = updated
        logger.info(f"[Mock] Event updated: {event_id}")
        return updated

    async def delete_event(self, event_id: str) -> bool:
        logger.debug(f"[Mock] Deleting event: {event_id}")
        if event_id not in self._store:
            return False
        del self._store[event_id]
        logger.info(f"[Mock] Event deleted: {event_id}")
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Real Microsoft Graph implementation
# ─────────────────────────────────────────────────────────────────────────────

class GraphCalendarService(BaseCalendarService):
    """
    Real implementation using Microsoft Graph SDK.
    Requires valid Azure credentials in settings.
    """

    def __init__(self) -> None:
        from core.auth import get_graph_client
        from config.settings import settings
        self._client = get_graph_client()
        self._user_id = settings.graph_user_id

    async def list_events(self, start: datetime, end: datetime) -> List[CalendarEvent]:
        logger.info(f"[Graph] Fetching events {start} → {end}")
        result = await (
            self._client.users
            .by_user_id(self._user_id)
            .calendar_view
            .get(request_configuration=lambda cfg: setattr(
                cfg.query_parameters, "start_date_time",
                start.isoformat()
            ) or setattr(cfg.query_parameters, "end_date_time", end.isoformat()))
        )
        events = []
        if result and result.value:
            for e in result.value:
                events.append(self._map(e))
        return events

    async def create_event(self, data: EventCreate) -> CalendarEvent:
        from msgraph.generated.models.event import Event
        from msgraph.generated.models.item_body import ItemBody
        from msgraph.generated.models.body_type import BodyType
        from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone as GDateTimeTimeZone
        from msgraph.generated.models.location import Location

        body = Event()
        body.subject = data.subject
        body.start = GDateTimeTimeZone(
            date_time=data.start.dateTime, time_zone=data.start.timeZone
        )
        body.end = GDateTimeTimeZone(
            date_time=data.end.dateTime, time_zone=data.end.timeZone
        )
        if data.body:
            body.body = ItemBody(content=data.body, content_type=BodyType.Text)
        if data.location:
            body.location = Location(display_name=data.location)
        body.is_online_meeting = data.is_online_meeting

        created = await self._client.users.by_user_id(self._user_id).events.post(body)
        return self._map(created)

    async def update_event(self, event_id: str, data: EventUpdate) -> CalendarEvent:
        from msgraph.generated.models.event import Event
        from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone as GDateTimeTimeZone

        patch = Event()
        if data.subject is not None:
            patch.subject = data.subject
        if data.start is not None:
            patch.start = GDateTimeTimeZone(date_time=data.start.dateTime, time_zone=data.start.timeZone)
        if data.end is not None:
            patch.end = GDateTimeTimeZone(date_time=data.end.dateTime, time_zone=data.end.timeZone)

        updated = await self._client.users.by_user_id(self._user_id).events.by_event_id(event_id).patch(patch)
        return self._map(updated)

    async def delete_event(self, event_id: str) -> bool:
        await self._client.users.by_user_id(self._user_id).events.by_event_id(event_id).delete()
        return True

    @staticmethod
    def _map(e) -> CalendarEvent:
        return CalendarEvent(
            id=e.id or "",
            subject=e.subject or "(Không có tiêu đề)",
            start=DateTimeTimeZone(dateTime=e.start.date_time, timeZone=e.start.time_zone),
            end=DateTimeTimeZone(dateTime=e.end.date_time, timeZone=e.end.time_zone),
            body=e.body.content if e.body else None,
            location=e.location.display_name if e.location else None,
            is_online_meeting=e.is_online_meeting or False,
            web_link=e.web_link,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def get_calendar_service() -> BaseCalendarService:
    """
    Factory: returns the correct calendar service based on settings.calendar_provider.

    CALENDAR_PROVIDER values:
      "mock"     → MockCalendarService (in-memory, no credentials needed)
      "google"   → GoogleCalendarService (Google Calendar via OAuth2)
      "msgraph"  → GraphCalendarService (Microsoft 365 via Azure)
    """
    from config.settings import settings

    provider = settings.calendar_provider.lower().strip()

    if provider == "mock" or settings.mock_graph:
        logger.info("Using MockCalendarService (provider=mock or MOCK_GRAPH=True)")
        return MockCalendarService()

    if provider == "google":
        logger.info("Using GoogleCalendarService (provider=google)")
        from services.google_calendar_service import GoogleCalendarService
        return GoogleCalendarService()

    if provider == "msgraph":
        logger.info("Using GraphCalendarService (provider=msgraph)")
        return GraphCalendarService()

    raise ValueError(
        f"Unknown CALENDAR_PROVIDER={provider!r}. "
        "Choose from: 'mock', 'google', 'msgraph'"
    )
