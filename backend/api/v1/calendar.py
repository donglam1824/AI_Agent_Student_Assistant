"""
api/v1/calendar.py
------------------
Calendar proxy endpoints:
  - GET  /calendar/events  → List upcoming events
  - POST /calendar/events  → Create a new event (via AI or direct)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from api.deps import get_current_user
from core.logger import logger

router = APIRouter(prefix="/calendar", tags=["Calendar"])


# ── Response Models ───────────────────────────────────────────────────────

class CalendarEvent(BaseModel):
    id: str
    summary: str
    start: str
    end: str
    location: Optional[str] = None
    description: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/events", response_model=list[CalendarEvent])
async def get_events(
    max_results: int = 20,
    current_user: User = Depends(get_current_user),
):
    """Get upcoming events from Google Calendar."""
    try:
        from services.google_calendar_service import GoogleCalendarService
        from datetime import datetime, timedelta, timezone
        service = GoogleCalendarService(user_id=current_user.id)
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=30)
        import asyncio
        events = asyncio.run(service.list_events(start=now, end=end))

        return [
            CalendarEvent(
                id=e.id,
                summary=e.subject,
                start=e.start.dateTime,
                end=e.end.dateTime,
                location=e.location,
                description=e.body,
            )
            for e in events[:max_results]
        ]
    except Exception as e:
        logger.error(f"Calendar API error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy lịch: {str(e)}")


@router.post("/events", response_model=CalendarEvent)
async def create_event(
    event: CalendarEvent,
    current_user: User = Depends(get_current_user),
):
    """Create a new event in Google Calendar."""
    try:
        import asyncio
        from services.google_calendar_service import GoogleCalendarService
        from models.calendar import EventCreate, DateTimeTimeZone
        service = GoogleCalendarService(user_id=current_user.id)

        data = EventCreate(
            subject=event.summary,
            start=DateTimeTimeZone(dateTime=event.start, timeZone="Asia/Ho_Chi_Minh"),
            end=DateTimeTimeZone(dateTime=event.end, timeZone="Asia/Ho_Chi_Minh"),
            body=event.description,
            location=event.location,
        )
        created = asyncio.run(service.create_event(data))

        return CalendarEvent(
            id=created.id,
            summary=created.subject,
            start=created.start.dateTime,
            end=created.end.dateTime,
            location=created.location,
            description=created.body,
        )
    except Exception as e:
        logger.error(f"Calendar create error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo sự kiện: {str(e)}")
