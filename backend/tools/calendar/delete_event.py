"""
tools/calendar/delete_event.py
-------------------------------
LangChain tool: delete a calendar event by ID.
Nhận user_id qua LangChain RunnableConfig.
"""

import asyncio

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger


@tool
def delete_calendar_event(event_id: str, config: RunnableConfig = None) -> str:
    """
    Xóa một sự kiện khỏi lịch theo ID.

    Args:
        event_id: ID của sự kiện cần xóa (lấy từ list_calendar_events).
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_calendar_service import GoogleCalendarService
    service = GoogleCalendarService(user_id=user_id)
    success = asyncio.run(service.delete_event(event_id))
    if success:
        logger.info(f"Deleted event: {event_id} for user={user_id}")
        return f"🗑️ Đã xóa sự kiện {event_id} thành công."
    return f"❌ Không tìm thấy sự kiện {event_id}."
