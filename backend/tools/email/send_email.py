"""
tools/email/send_email.py
-------------------------
LangChain tool to send an email.
"""

import asyncio
from typing import List, Optional
from langchain_core.tools import tool
from services.graph_email_service import get_email_service
from models.email import EmailCreate
from core.logger import logger

@tool
def send_email(subject: str, body: str, to_recipients: List[str], cc_recipients: Optional[List[str]] = None) -> str:
    """
    Send an email.
    
    Args:
        subject: Subject of the email
        body: Body content of the email
        to_recipients: List of recipient email addresses
        cc_recipients: Optional list of CC email addresses
    """
    service = get_email_service()
    data = EmailCreate(
        subject=subject,
        body=body,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients
    )
    try:
        success = asyncio.run(service.send_email(data))
        if success:
            return f"Đã gửi email '{subject}' thành công đến {', '.join(to_recipients)}."
        return "Gửi email thất bại."
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return f"Lỗi khi gửi email: {e}"
