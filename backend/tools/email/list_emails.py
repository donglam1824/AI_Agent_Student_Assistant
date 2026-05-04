"""
tools/email/list_emails.py
--------------------------
LangChain tool to list emails.
Nhận user_id qua LangChain RunnableConfig.
"""

import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger


@tool
def list_emails(limit: int = 5, config: RunnableConfig = None) -> str:
    """
    Get the most recent emails from the user's inbox.

    Args:
        limit: Number of emails to retrieve (default: 5)
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_email_service import GoogleEmailService
    service = GoogleEmailService(user_id=user_id)
    try:
        emails = asyncio.run(service.list_emails(limit=limit))
        if not emails:
            return "Không có email nào."

        lines = [f"📧 Danh sách {len(emails)} email gần đây:"]
        for e in emails:
            lines.append(
                f"  • [{e.id[:8]}] Từ: {e.sender} | Tiêu đề: {e.subject}\n"
                f"    Xem trước: {e.body_preview[:80]}...\n"
                f"    Nhận lúc: {e.received_date_time}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing emails for user={user_id}: {e}")
        return f"Lỗi khi lấy email: {e}"
