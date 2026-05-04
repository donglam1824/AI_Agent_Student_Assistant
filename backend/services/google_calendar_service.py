"""
services/google_calendar_service.py
------------------------------------
Google Calendar API implementation – multi-tenant, token từ Database.

Mỗi request, service nhận user_id, truy vấn DB để lấy token đã mã hóa,
giải mã và dùng để gọi Google Calendar API. Nếu token hết hạn, tự refresh
và lưu lại token mới vào DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.calendar import CalendarEvent, DateTimeTimeZone, EventCreate, EventUpdate
from services.graph_calendar_service import BaseCalendarService
from core.logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]
DEFAULT_TZ = "Asia/Ho_Chi_Minh"


def _get_credentials_from_db(user_id: str) -> Credentials:
    """
    Truy vấn DB lấy token đã mã hóa của user, giải mã và tạo Credentials.
    Tự động refresh nếu hết hạn và lưu token mới vào DB.
    """
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

        # Refresh nếu hết hạn
        if not creds.valid and creds.refresh_token:
            logger.info(f"[Google Calendar] Refreshing token for user={user_id}")
            creds.refresh(Request())
            # Lưu token mới vào DB
            crud.update_user_tokens(
                db=db,
                user_id=user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
            )
            logger.info(f"[Google Calendar] Token refreshed and saved for user={user_id}")

        return creds
    finally:
        db.close()


class GoogleCalendarService(BaseCalendarService):
    """
    Google Calendar implementation – đa người dùng, token từ Database.
    """

    def __init__(self, user_id: str) -> None:
        from config.settings import settings
        creds = _get_credentials_from_db(user_id)
        self._service = build("calendar", "v3", credentials=creds)
        self._calendar_id = settings.google_calendar_id
        self._user_id = user_id
        logger.info(f"[Google Calendar] Service ready for user={user_id}")

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _to_rfc3339(dt_str: str, tz: str = DEFAULT_TZ) -> str:
        """Chuyển 'YYYY-MM-DDTHH:MM:SS' sang RFC3339 với timezone offset."""
        import pytz
        naive = datetime.fromisoformat(dt_str)
        local_tz = pytz.timezone(tz)
        aware = local_tz.localize(naive)
        return aware.isoformat()

    @staticmethod
    def _from_google_event(g: dict) -> CalendarEvent:
        """Map Google API event dict → CalendarEvent model."""
        start = g.get("start", {})
        end = g.get("end", {})
        start_dt = start.get("dateTime", start.get("date", ""))
        end_dt = end.get("dateTime", end.get("date", ""))
        start_tz = start.get("timeZone", DEFAULT_TZ)
        end_tz = end.get("timeZone", DEFAULT_TZ)
        return CalendarEvent(
            id=g.get("id", ""),
            subject=g.get("summary", "(Không có tiêu đề)"),
            start=DateTimeTimeZone(dateTime=start_dt, timeZone=start_tz),
            end=DateTimeTimeZone(dateTime=end_dt, timeZone=end_tz),
            body=g.get("description"),
            location=g.get("location"),
            is_online_meeting=bool(g.get("conferenceData")),
            web_link=g.get("htmlLink"),
        )

    # ── CRUD ───────────────────────────────────────────────────────────────

    async def list_events(self, start: datetime, end: datetime) -> List[CalendarEvent]:
        logger.info(f"[Google Calendar] user={self._user_id} listing events {start.isoformat()} → {end.isoformat()}")
        try:
            result = (
                self._service.events()
                .list(
                    calendarId=self._calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=50,
                )
                .execute()
            )
            items = result.get("items", [])
            return [self._from_google_event(e) for e in items]
        except HttpError as e:
            logger.error(f"[Google Calendar] list_events error: {e}")
            raise

    async def create_event(self, data: EventCreate) -> CalendarEvent:
        logger.info(f"[Google Calendar] user={self._user_id} creating event: {data.subject!r}")
        tz = data.start.timeZone or DEFAULT_TZ
        body = {
            "summary": data.subject,
            "start": {"dateTime": self._to_rfc3339(data.start.dateTime, tz), "timeZone": tz},
            "end": {"dateTime": self._to_rfc3339(data.end.dateTime, data.end.timeZone or tz), "timeZone": data.end.timeZone or tz},
        }
        if data.body:
            body["description"] = data.body
        if data.location:
            body["location"] = data.location
        if data.is_online_meeting:
            body["conferenceData"] = {"createRequest": {"requestId": "meet-" + data.subject[:8]}}
        try:
            conference_version = 1 if data.is_online_meeting else 0
            created = (
                self._service.events()
                .insert(calendarId=self._calendar_id, body=body, conferenceDataVersion=conference_version)
                .execute()
            )
            return self._from_google_event(created)
        except HttpError as e:
            logger.error(f"[Google Calendar] create_event error: {e}")
            raise

    async def update_event(self, event_id: str, data: EventUpdate) -> CalendarEvent:
        logger.info(f"[Google Calendar] user={self._user_id} updating event: {event_id}")
        try:
            existing = self._service.events().get(calendarId=self._calendar_id, eventId=event_id).execute()
            if data.subject is not None:
                existing["summary"] = data.subject
            if data.body is not None:
                existing["description"] = data.body
            if data.location is not None:
                existing["location"] = data.location
            if data.start is not None:
                tz = data.start.timeZone or DEFAULT_TZ
                existing["start"] = {"dateTime": self._to_rfc3339(data.start.dateTime, tz), "timeZone": tz}
            if data.end is not None:
                tz = data.end.timeZone or DEFAULT_TZ
                existing["end"] = {"dateTime": self._to_rfc3339(data.end.dateTime, tz), "timeZone": tz}
            updated = (
                self._service.events()
                .update(calendarId=self._calendar_id, eventId=event_id, body=existing)
                .execute()
            )
            return self._from_google_event(updated)
        except HttpError as e:
            logger.error(f"[Google Calendar] update_event error: {e}")
            raise

    async def delete_event(self, event_id: str) -> bool:
        logger.info(f"[Google Calendar] user={self._user_id} deleting event: {event_id}")
        try:
            self._service.events().delete(calendarId=self._calendar_id, eventId=event_id).execute()
            return True
        except HttpError as e:
            logger.error(f"[Google Calendar] delete_event error: {e}")
            return False
