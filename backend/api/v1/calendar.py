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
        service = GoogleCalendarService()
        events = service.list_upcoming_events(max_results=max_results)

        return [
            CalendarEvent(
                id=e.get("id", ""),
                summary=e.get("summary", "Không có tiêu đề"),
                start=e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
                end=e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
                location=e.get("location"),
                description=e.get("description"),
            )
            for e in events
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
        from services.google_calendar_service import GoogleCalendarService
        service = GoogleCalendarService()

        event_body = {
            "summary": event.summary,
            "start": {"dateTime": event.start, "timeZone": "Asia/Ho_Chi_Minh"},
            "end": {"dateTime": event.end, "timeZone": "Asia/Ho_Chi_Minh"},
        }
        if event.location:
            event_body["location"] = event.location
        if event.description:
            event_body["description"] = event.description

        created = service.create_event(event_body)

        return CalendarEvent(
            id=created.get("id", ""),
            summary=created.get("summary", ""),
            start=created.get("start", {}).get("dateTime", ""),
            end=created.get("end", {}).get("dateTime", ""),
            location=created.get("location"),
            description=created.get("description"),
        )
    except Exception as e:
        logger.error(f"Calendar create error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo sự kiện: {str(e)}")
