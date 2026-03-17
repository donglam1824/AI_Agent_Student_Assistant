"""
tools/calendar/list_events.py
------------------------------
LangChain tool: list calendar events within a date range.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from langchain_core.tools import tool

from services.graph_calendar_service import get_calendar_service
from core.logger import logger


@tool
def list_calendar_events(days_ahead: int = 7) -> str:
    """
    Liệt kê các sự kiện lịch sắp tới trong N ngày tiếp theo.

    Args:
        days_ahead: Số ngày muốn xem phía trước (mặc định 7 ngày).

    Returns:
        Danh sách sự kiện dạng văn bản.
    """
    service = get_calendar_service()
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
