"""
tools/email/list_emails.py
--------------------------
LangChain tool to list emails.
"""

import asyncio
from langchain_core.tools import tool
from services.graph_email_service import get_email_service
from core.logger import logger

@tool
def list_emails(limit: int = 5) -> str:
    """
    Get the most recent emails from the user's inbox.
    
    Args:
        limit: Number of emails to retrieve (default: 5)
    """
    service = get_email_service()
    try:
        emails = asyncio.run(service.list_emails(limit=limit))
        if not emails:
            return "Không có email nào."
        
        lines = [f"📧 Danh sách {len(emails)} email gần đây:"]
        for e in emails:
            lines.append(f"  • [{e.id[:8]}] Từ: {e.sender} | Tiêu đề: {e.subject}\n    Xem trước: {e.body_preview[:50]}...\n    Nhận lúc: {e.received_date_time}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        return f"Lỗi khi lấy email: {e}"
