"""
tools/email/list_emails.py
--------------------------
LangChain tool to list emails from Gmail, Outlook, or both.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_emails(source: str = "all", limit: int = 5, config: RunnableConfig = None) -> str:
    """
    Get recent emails from Gmail, Outlook, or both mailboxes.

    Args:
        source: Email source: "all", "gmail", or "outlook".
        limit: Number of emails to retrieve.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Loi: Khong tim thay thong tin nguoi dung. Vui long dang nhap lai."

    from services.graph_email_service import get_email_service

    service = get_email_service(user_id=user_id)
    try:
        emails = asyncio.run(service.list_emails(limit=limit, source=source))
        if not emails:
            return "Khong co email nao."

        lines = [f"Danh sach {len(emails)} email gan day:"]
        for email in emails:
            source_label = (email.source or "email").upper()
            lines.append(
                f"- [{email.id}] Nguon: {source_label} | Tu: {email.sender} | Tieu de: {email.subject}\n"
                f"  Xem truoc: {email.body_preview[:120]}\n"
                f"  Nhan luc: {email.received_date_time}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing emails for user={user_id}: {e}")
        return f"Loi khi lay email: {e}"
