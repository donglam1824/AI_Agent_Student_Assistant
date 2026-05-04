"""
tools/calendar/list_events.py
------------------------------
LangChain tool: list calendar events within a date range.
Nhận user_id qua LangChain RunnableConfig để hỗ trợ đa người dùng.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger


@tool
def list_calendar_events(days_ahead: int = 7, config: RunnableConfig = None) -> str:
    """
    Liệt kê các sự kiện lịch sắp tới trong N ngày tiếp theo.

    Args:
        days_ahead: Số ngày muốn xem phía trước (mặc định 7 ngày).

    Returns:
        Danh sách sự kiện dạng văn bản.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_calendar_service import GoogleCalendarService
    service = GoogleCalendarService(user_id=user_id)
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)

    events = asyncio.run(service.list_events(start=now, end=end))

    if not events:
        return f"Không có sự kiện nào trong {days_ahead} ngày tới."

    lines = [f"📅 Lịch {days_ahead} ngày tới ({len(events)} sự kiện):"]
    for evt in events:
        lines.append(
            f"  • [{evt.id[:8]}] {evt.subject}\n"
            f"    🕐 {evt.start.dateTime} → {evt.end.dateTime}\n"
            f"    📍 {evt.location or 'Không có địa điểm'}"
        )
    return "\n".join(lines)
