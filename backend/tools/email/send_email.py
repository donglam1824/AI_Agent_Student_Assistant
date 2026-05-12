"""
tools/email/send_email.py
-------------------------
LangChain tool to send email through Gmail or Outlook.
"""

import asyncio
from typing import List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger
from models.email import EmailCreate


@tool
def send_email(
    subject: str,
    body: str,
    to_recipients: List[str],
    cc_recipients: Optional[List[str]] = None,
    source: str = "gmail",
    config: RunnableConfig = None,
) -> str:
    """
    Send an email from Gmail or Outlook.

    Args:
        subject: Email subject.
        body: Email body.
        to_recipients: Recipient email addresses.
        cc_recipients: Optional CC recipient email addresses.
        source: Sending mailbox: "gmail" or "outlook".
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Loi: Khong tim thay thong tin nguoi dung. Vui long dang nhap lai."

    from services.graph_email_service import get_email_service

    service = get_email_service(user_id=user_id)
    data = EmailCreate(
        subject=subject,
        body=body,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        source=source,
    )
    try:
        success = asyncio.run(service.send_email(data))
        if success:
            return f"Da gui email tu {source} voi tieu de '{subject}' den {', '.join(to_recipients)}."
        return "Gui email that bai."
    except Exception as e:
        logger.error(f"Error sending email for user={user_id}: {e}")
        return f"Loi khi gui email: {e}"
