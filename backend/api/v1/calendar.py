"""
api/v1/calendar.py
------------------
Calendar proxy endpoints:
  - GET  /calendar/events  → List upcoming events
  - POST /calendar/events  → Create a new event (via AI or direct)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
    max_results: int = 50,
    time_min: Optional[str] = Query(None, description="ISO 8601 start of range"),
    time_max: Optional[str] = Query(None, description="ISO 8601 end of range"),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming events from Google Calendar."""
    try:
        from services.google_calendar_service import GoogleCalendarService

        service = GoogleCalendarService(user_id=current_user.id)

        # Parse time range or use defaults (past 30 days → future 60 days)
        if time_min:
            start = datetime.fromisoformat(time_min)
        else:
            start = datetime.now(timezone.utc) - timedelta(days=30)

        if time_max:
            end = datetime.fromisoformat(time_max)
        else:
            end = datetime.now(timezone.utc) + timedelta(days=60)

        # Await directly – do NOT use asyncio.run() inside async handlers
        events = await service.list_events(start=start, end=end)

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
        logger.error(f"Calendar API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy lịch: {str(e)}")


@router.post("/events", response_model=CalendarEvent)
async def create_event(
    event: CalendarEvent,
    current_user: User = Depends(get_current_user),
):
    """Create a new event in Google Calendar."""
    try:
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
        # Await directly – do NOT use asyncio.run() inside async handlers
        created = await service.create_event(data)

        return CalendarEvent(
            id=created.id,
            summary=created.subject,
            start=created.start.dateTime,
            end=created.end.dateTime,
            location=created.location,
            description=created.body,
        )
    except Exception as e:
        logger.error(f"Calendar create error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo sự kiện: {str(e)}")
