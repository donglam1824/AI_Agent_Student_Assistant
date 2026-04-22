"""
models/calendar.py
------------------
Pydantic schemas for Calendar events.
These models are the contract between layers (service ↔ tools ↔ agent).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DateTimeTimeZone(BaseModel):
    """Microsoft Graph dateTimeTimeZone structure."""
    dateTime: str = Field(..., description="ISO 8601 datetime string, e.g. '2026-03-17T09:00:00'")
    timeZone: str = Field(default="Asia/Ho_Chi_Minh")


class EventCreate(BaseModel):
    """Input model for creating a new calendar event."""
    subject: str = Field(..., description="Title of the event")
    start: DateTimeTimeZone = Field(..., description="Start date and time")
    end: DateTimeTimeZone = Field(..., description="End date and time")
    body: Optional[str] = Field(default=None, description="Event description / notes")
    location: Optional[str] = Field(default=None, description="Event location")
    is_online_meeting: bool = Field(default=False, description="Whether this is a Teams meeting")


class EventUpdate(BaseModel):
    """Input model for updating an existing calendar event (all fields optional)."""
    subject: Optional[str] = None
    start: Optional[DateTimeTimeZone] = None
    end: Optional[DateTimeTimeZone] = None
    body: Optional[str] = None
    location: Optional[str] = None
    is_online_meeting: Optional[bool] = None


class CalendarEvent(BaseModel):
    """Output model representing a calendar event returned from the Graph API."""
    id: str = Field(..., description="Graph event ID")
    subject: str
    start: DateTimeTimeZone
    end: DateTimeTimeZone
    body: Optional[str] = None
    location: Optional[str] = None
    is_online_meeting: bool = False
    web_link: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
