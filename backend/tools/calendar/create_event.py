"""
tools/calendar/create_event.py
-------------------------------
LangChain tool: create a new calendar event.
Nhận user_id qua LangChain RunnableConfig.
"""

import asyncio

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from models.calendar import EventCreate, DateTimeTimeZone
from core.logger import logger


@tool
def create_calendar_event(
    subject: str,
    start_datetime: str,
    end_datetime: str,
    body: str = "",
    location: str = "",
    timezone: str = "Asia/Ho_Chi_Minh",
    config: RunnableConfig = None,
) -> str:
    """
    Tạo một sự kiện mới trên lịch.

    Args:
        subject: Tiêu đề sự kiện.
        start_datetime: Thời gian bắt đầu theo định dạng 'YYYY-MM-DDTHH:MM:SS'.
        end_datetime: Thời gian kết thúc theo định dạng 'YYYY-MM-DDTHH:MM:SS'.
        body: Mô tả / ghi chú cho sự kiện (tùy chọn).
        location: Địa điểm (tùy chọn).
        timezone: Múi giờ (mặc định Asia/Ho_Chi_Minh).

    Returns:
        Thông báo tạo sự kiện thành công kèm ID.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_calendar_service import GoogleCalendarService
    service = GoogleCalendarService(user_id=user_id)
    data = EventCreate(
        subject=subject,
        start=DateTimeTimeZone(dateTime=start_datetime, timeZone=timezone),
        end=DateTimeTimeZone(dateTime=end_datetime, timeZone=timezone),
        body=body or None,
        location=location or None,
    )
    event = asyncio.run(service.create_event(data))
    logger.info(f"Created event: {event.id} for user={user_id}")
    return (
        f"✅ Đã tạo sự kiện thành công!\n"
        f"  ID:    {event.id}\n"
        f"  Tiêu đề: {event.subject}\n"
        f"  Bắt đầu: {event.start.dateTime}\n"
        f"  Kết thúc: {event.end.dateTime}\n"
        f"  Địa điểm: {event.location or 'Không có'}"
    )
