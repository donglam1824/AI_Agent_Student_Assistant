"""
tools/email/send_email.py
-------------------------
LangChain tool to send an email.
Nhận user_id qua LangChain RunnableConfig.
"""

import asyncio
from typing import List, Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from models.email import EmailCreate
from core.logger import logger


@tool
def send_email(
    subject: str,
    body: str,
    to_recipients: List[str],
    cc_recipients: Optional[List[str]] = None,
    config: RunnableConfig = None,
) -> str:
    """
    Gửi một email đến người nhận.

    Args:
        subject: Tiêu đề email.
        body: Nội dung email.
        to_recipients: Danh sách địa chỉ email người nhận.
        cc_recipients: Danh sách địa chỉ CC (tùy chọn).
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_email_service import GoogleEmailService
    service = GoogleEmailService(user_id=user_id)
    data = EmailCreate(
        subject=subject,
        body=body,
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
    )
    try:
        success = asyncio.run(service.send_email(data))
        if success:
            return f"✅ Đã gửi email '{subject}' thành công đến {', '.join(to_recipients)}."
        return "❌ Gửi email thất bại."
    except Exception as e:
        logger.error(f"Error sending email for user={user_id}: {e}")
        return f"Lỗi khi gửi email: {e}"
