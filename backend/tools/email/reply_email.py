"""
tools/email/reply_email.py
--------------------------
LangChain tool to reply to Gmail or Outlook messages.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def reply_email(message_id: str, body: str, config: RunnableConfig = None) -> str:
    """
    Reply to an existing email.

    Args:
        message_id: Message ID returned by list_emails. It should look like
            "gmail:<id>" or "outlook:<id>" when both mailboxes are enabled.
        body: Reply body.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Loi: Khong tim thay thong tin nguoi dung. Vui long dang nhap lai."

    from services.graph_email_service import get_email_service

    service = get_email_service(user_id=user_id)
    try:
        success = asyncio.run(service.reply_email(message_id=message_id, body=body))
        if success:
            return f"Da tra loi email {message_id}."
        return "Tra loi email that bai."
    except Exception as e:
        logger.error(f"Error replying email for user={user_id}: {e}")
        return f"Loi khi tra loi email: {e}"
