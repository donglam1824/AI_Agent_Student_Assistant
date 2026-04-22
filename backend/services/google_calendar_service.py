"""
services/google_calendar_service.py
------------------------------------
Google Calendar API implementation (OAuth2 – Desktop/Installed app flow).

Flow lần đầu:
  1. Mở trình duyệt → user đăng nhập Google → cấp quyền Calendar
  2. Token được lưu vào GOOGLE_TOKEN_PATH (mặc định: token_google.json)
  3. Các lần sau dùng lại token (tự refresh nếu hết hạn)

Scopes cần thiết (phải bật trên Google Cloud Console):
  - https://www.googleapis.com/auth/calendar
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.calendar import CalendarEvent, DateTimeTimeZone, EventCreate, EventUpdate
from services.graph_calendar_service import BaseCalendarService
from core.logger import logger

# Google Calendar read + write scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Timezone mặc định cho VN
DEFAULT_TZ = "Asia/Ho_Chi_Minh"


def _get_credentials(credentials_path: str, token_path: str) -> Credentials:
    """
    Load hoặc tạo mới OAuth2 credentials.
    Lần đầu sẽ mở Browser để user đăng nhập.
    """
    creds: Credentials | None = None

    # Thử load token đã lưu
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Nếu chưa có hoặc hết hạn → refresh / login lại
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("[Google] Refreshing expired token...")
            creds.refresh(Request())
        else:
            logger.info("[Goog le] No valid token. Starting OAuth2 flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            try:
                # Thử mở local server trước
                creds = flow.run_local_server(port=0, timeout_seconds=15)
            except Exception as e:
                logger.warning(f"[Google] Local server failed ({e}). Falling back to manual auth.")
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                auth_url, _ = flow.authorization_url(prompt='consent')
                print("\n" + "="*60)
                print("⚠️ KHÔNG THỂ TỰ ĐỘNG BẮT MÃ XÁC THỰC ⚠️")
                print("1. Hãy mở đường link sau trong trình duyệt:")
                print(auth_url)
                code = input("\n2. Nhập mã code bạn nhận được từ Google: ").strip()
                print("="*60 + "\n")
                flow.fetch_token(code=code)
                creds = flow.credentials

        # Lưu token để dùng lại
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info(f"[Google] Token saved to {token_path}")

    return creds


class GoogleCalendarService(BaseCalendarService):
    """
    Google Calendar implementation of BaseCalendarService.
    Dùng OAuth2 InstalledApp flow – phù hợp cho desktop / dev.
    """

    def __init__(self) -> None:
        from config.settings import settings
        creds = _get_credentials(
            credentials_path=settings.google_credentials_path,
            token_path=settings.google_token_path,
        )
        self._service = build("calendar", "v3", credentials=creds)
        self._calendar_id = settings.google_calendar_id
        logger.info(f"[Google] Calendar service ready. calendar_id={self._calendar_id!r}")

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _to_rfc3339(dt_str: str, tz: str = DEFAULT_TZ) -> str:
        """Chuyển 'YYYY-MM-DDTHH:MM:SS' sang RFC3339 với timezone offset."""
        from datetime import datetime
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

        # Support all-day events (dateOnly) and timed events (dateTime)
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
        logger.info(f"[Google] Listing events {start.isoformat()} → {end.isoformat()}")
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
            logger.debug(f"[Google] Found {len(items)} events")
            return [self._from_google_event(e) for e in items]
        except HttpError as e:
            logger.error(f"[Google] list_events error: {e}")
            raise

    async def create_event(self, data: EventCreate) -> CalendarEvent:
        logger.info(f"[Google] Creating event: {data.subject!r}")
        tz = data.start.timeZone or DEFAULT_TZ
        body = {
            "summary": data.subject,
            "start": {
                "dateTime": self._to_rfc3339(data.start.dateTime, tz),
                "timeZone": tz,
            },
            "end": {
                "dateTime": self._to_rfc3339(data.end.dateTime, data.end.timeZone or tz),
                "timeZone": data.end.timeZone or tz,
            },
        }
        if data.body:
            body["description"] = data.body
        if data.location:
            body["location"] = data.location
        if data.is_online_meeting:
            body["conferenceData"] = {
                "createRequest": {"requestId": "meet-" + data.subject[:8]}
            }

        try:
            conference_version = 1 if data.is_online_meeting else 0
            created = (
                self._service.events()
                .insert(
                    calendarId=self._calendar_id,
                    body=body,
                    conferenceDataVersion=conference_version,
                )
                .execute()
            )
            logger.info(f"[Google] Event created: {created['id']} – {created.get('summary')}")
            return self._from_google_event(created)
        except HttpError as e:
            logger.error(f"[Google] create_event error: {e}")
            raise

    async def update_event(self, event_id: str, data: EventUpdate) -> CalendarEvent:
        logger.info(f"[Google] Updating event: {event_id}")
        try:
            # Fetch existing first
            existing = self._service.events().get(
                calendarId=self._calendar_id, eventId=event_id
            ).execute()

            # Apply partial updates
            if data.subject is not None:
                existing["summary"] = data.subject
            if data.body is not None:
                existing["description"] = data.body
            if data.location is not None:
                existing["location"] = data.location
            if data.start is not None:
                tz = data.start.timeZone or DEFAULT_TZ
                existing["start"] = {
                    "dateTime": self._to_rfc3339(data.start.dateTime, tz),
                    "timeZone": tz,
                }
            if data.end is not None:
                tz = data.end.timeZone or DEFAULT_TZ
                existing["end"] = {
                    "dateTime": self._to_rfc3339(data.end.dateTime, tz),
                    "timeZone": tz,
                }

            updated = (
                self._service.events()
                .update(calendarId=self._calendar_id, eventId=event_id, body=existing)
                .execute()
            )
            logger.info(f"[Google] Event updated: {event_id}")
            return self._from_google_event(updated)
        except HttpError as e:
            logger.error(f"[Google] update_event error: {e}")
            raise

    async def delete_event(self, event_id: str) -> bool:
        logger.info(f"[Google] Deleting event: {event_id}")
        try:
            self._service.events().delete(
                calendarId=self._calendar_id, eventId=event_id
            ).execute()
            logger.info(f"[Google] Event deleted: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"[Google] delete_event error: {e}")
            return False
