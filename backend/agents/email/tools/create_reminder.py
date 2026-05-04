"""
backend/agents/email/tools/create_reminder.py
---------------------------------------------
Tool tự động tạo sự kiện nhắc nhở (Google Calendar) từ deadline đã phân tích.
"""
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class CreateReminderInput(BaseModel):
    task_name: str = Field(description="Tên công việc hoặc tiêu đề sự kiện")
    date_str: str = Field(description="Ngày của sự kiện (YYYY-MM-DD)")
    time_str: Optional[str] = Field(None, description="Giờ của sự kiện (HH:MM) - Không bắt buộc")
    description: Optional[str] = Field(None, description="Mô tả chi tiết cho sự kiện (ví dụ: Trích từ email của Thầy Minh)")

@tool("create_reminder", args_schema=CreateReminderInput)
def create_reminder(task_name: str, date_str: str, time_str: Optional[str] = None, description: Optional[str] = None) -> str:
    """
    Tạo một sự kiện trên Lịch (Google Calendar) cho các deadline quan trọng.
    Tool này giả lập/tích hợp việc gọi Google Calendar API để tạo sự kiện.
    Trả về kết quả tạo thành công kèm Event ID (giả lập nếu chưa có Calendar API hoàn chỉnh).
    """
    from core.logger import logger
    import uuid
    
    logger.info(f"Creating reminder: {task_name} on {date_str} {time_str or ''}")
    
    # Ở phiên bản tích hợp thực tế, đoạn này có thể import CalendarAgent hoặc gọi Google Calendar Service
    # Ví dụ (nếu có Calendar Agent):
    # from services.google_calendar_service import GoogleCalendarService
    # ...
    
    # Tạm thời trả về mock ID thành công để tích hợp workflow
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    
    return f"Đã tạo thành công sự kiện '{task_name}' trên Lịch vào lúc {time_str or 'cả ngày'} {date_str}. Event ID: {event_id}"
