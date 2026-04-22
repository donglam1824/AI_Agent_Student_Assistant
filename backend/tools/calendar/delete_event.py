"""
tools/calendar/delete_event.py
-------------------------------
LangChain tool: delete a calendar event by ID.
"""

import asyncio

from langchain_core.tools import tool

from services.graph_calendar_service import get_calendar_service
from core.logger import logger


@tool
def delete_calendar_event(event_id: str) -> str:
    """
    Xóa một sự kiện khỏi lịch theo ID.

    Args:
        event_id: ID của sự kiện cần xóa (lấy từ list_calendar_events).

    Returns:
        Thông báo xóa thành công hoặc thất bại.
    """
    service = get_calendar_service()
    success = asyncio.run(service.delete_event(event_id))
    if success:
        logger.info(f"Deleted event: {event_id}")
        return f"🗑️ Đã xóa sự kiện {event_id} thành công."
    return f"❌ Không tìm thấy sự kiện {event_id}."
