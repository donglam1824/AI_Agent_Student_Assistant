"""
tools/email/list_emails.py
--------------------------
LangChain tool to list emails from Gmail, Outlook, or both.
Supports academic-only filtering.
"""

import asyncio

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


@tool
def list_emails(
    source: str = "all",
    limit: int = 5,
    academic_only: bool = True,
    config: RunnableConfig = None,
) -> str:
    """
    Lấy danh sách email từ Gmail, Outlook, hoặc cả hai.
    Mặc định chỉ lấy email học thuật. Đặt academic_only=False để xem tất cả.

    Args:
        source: Nguồn email: "all", "gmail", hoặc "outlook".
        limit: Số lượng email tối đa.
        academic_only: Nếu True, chỉ trả về email học thuật (mặc định True).
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.graph_email_service import get_email_service

    service = get_email_service(user_id=user_id)
    try:
        # Lấy nhiều hơn limit nếu cần lọc academic (vì sau khi lọc có thể ít hơn)
        fetch_limit = limit * 3 if academic_only else limit
        emails = asyncio.run(service.list_emails(limit=fetch_limit, source=source))

        if not emails:
            return "Không có email nào."

        # Lọc academic nếu cần
        if academic_only:
            from services.academic_filter import filter_academic_emails
            academic_emails, _ = filter_academic_emails(emails, user_id=user_id)
            emails = academic_emails[:limit]

            if not emails:
                return (
                    "Không có email học thuật nào gần đây. "
                    "Bạn có muốn xem tất cả email không? "
                    "(Gọi lại list_emails với academic_only=False)"
                )
        else:
            emails = emails[:limit]

        # Format output
        label = "email học thuật" if academic_only else "email"
        lines = [f"Danh sách {len(emails)} {label} gần đây:"]
        for email in emails:
            source_label = (email.source or "email").upper()
            # Body preview giới hạn 80 ký tự
            preview = (email.body_preview or "")[:80]
            lines.append(
                f"- [{email.id}] Nguồn: {source_label} | Từ: {email.sender} | "
                f"Tiêu đề: {email.subject}\n"
                f"  Xem trước: {preview}\n"
                f"  Nhận lúc: {email.received_date_time}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing emails for user={user_id}: {e}")
        return f"Lỗi khi lấy email: {e}"
