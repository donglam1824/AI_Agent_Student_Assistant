"""
tools/calendar/update_event.py
-------------------------------
LangChain tool: update an existing calendar event.
"""

import asyncio
from typing import Optional

from langchain_core.tools import tool

from services.graph_calendar_service import get_calendar_service
from models.calendar import EventUpdate, DateTimeTimeZone
from core.logger import logger


@tool
def update_calendar_event(
    event_id: str,
    subject: str = "",
    start_datetime: str = "",
    end_datetime: str = "",
    body: str = "",
    location: str = "",
    timezone: str = "Asia/Ho_Chi_Minh",
) -> str:
    """
    Cập nhật thông tin một sự kiện lịch theo ID.

    Args:
        event_id: ID của sự kiện cần cập nhật (lấy từ list_calendar_events).
        subject: Tiêu đề mới (để trống nếu không đổi).
        start_datetime: Thời gian bắt đầu mới (để trống nếu không đổi).
        end_datetime: Thời gian kết thúc mới (để trống nếu không đổi).
        body: Mô tả mới (để trống nếu không đổi).
        location: Địa điểm mới (để trống nếu không đổi).
        timezone: Múi giờ (mặc định Asia/Ho_Chi_Minh).

    Returns:
        Kết quả cập nhật.
    """
    service = get_calendar_service()
    data = EventUpdate(
        subject=subject or None,
        start=DateTimeTimeZone(dateTime=start_datetime, timeZone=timezone) if start_datetime else None,
        end=DateTimeTimeZone(dateTime=end_datetime, timeZone=timezone) if end_datetime else None,
        body=body or None,
        location=location or None,
    )
    updated = asyncio.run(service.update_event(event_id, data))
    logger.info(f"Updated event: {updated.id}")
    return (
        f"✅ Đã cập nhật sự kiện!\n"
        f"  ID:    {updated.id}\n"
        f"  Tiêu đề: {updated.subject}\n"
        f"  Bắt đầu: {updated.start.dateTime}\n"
        f"  Kết thúc: {updated.end.dateTime}"
    )
