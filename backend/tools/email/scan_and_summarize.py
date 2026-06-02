"""
tools/email/scan_and_summarize.py
----------------------------------
LangChain tool: quét email → lọc học thuật → phân loại ưu tiên → trình bày
có cấu trúc theo Smart mode.
"""

import asyncio
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


PRIORITY_ICONS = {
    "urgent": "🔴 KHẨN CẤP",
    "important": "🟡 QUAN TRỌNG",
    "follow_up": "🔵 CẦN PHẢN HỒI",
    "info": "🟢 THÔNG TIN",
}

PRIORITY_ORDER = ["urgent", "important", "follow_up", "info"]

# Số email non-academic hiển thị khi không có email học thuật (Smart mode)
SMART_FALLBACK_LIMIT = 3


def _format_time(received_date_time: str) -> str:
    """Trích xuất giờ:phút từ chuỗi datetime để hiển thị ngắn gọn."""
    from datetime import datetime

    if not received_date_time:
        return ""

    # Thử parse ISO format
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(received_date_time.split("+")[0].split(".")[0], fmt.split("+")[0].split(".")[0])
            return dt.strftime("%H:%M %d/%m")
        except ValueError:
            continue

    # Thử parse email date format
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(received_date_time)
        return dt.strftime("%H:%M %d/%m")
    except Exception:
        pass

    return received_date_time[:16] if len(received_date_time) > 16 else received_date_time


@tool
def scan_and_summarize_emails(
    source: str = "all",
    limit: int = 10,
    config: RunnableConfig = None,
) -> str:
    """
    Quét hộp thư, lọc chỉ email học thuật, phân loại ưu tiên và trình bày có cấu trúc.
    Đây là tool ưu tiên khi sinh viên muốn kiểm tra email mới.

    Args:
        source: Nguồn email: "all", "gmail", hoặc "outlook".
        limit: Số lượng email tối đa cần quét.
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.graph_email_service import get_email_service
    from services.academic_filter import filter_academic_emails
    from agents.email.tools.analyze_priority import analyze_priority

    service = get_email_service(user_id=user_id)

    try:
        # 1. Lấy email từ hộp thư
        all_emails = asyncio.run(service.list_emails(limit=limit, source=source))
        if not all_emails:
            return "Không có email nào trong hộp thư."

        # 2. Lọc email học thuật
        academic_emails, non_academic_emails = filter_academic_emails(
            all_emails, user_id=user_id
        )

        # 3. Nếu CÓ email học thuật → phân loại ưu tiên và trình bày
        if academic_emails:
            return _format_academic_results(academic_emails, analyze_priority)

        # 4. Nếu KHÔNG có email học thuật → Smart mode fallback
        return _format_smart_fallback(non_academic_emails)

    except Exception as e:
        logger.error(f"Error scanning emails for user={user_id}: {e}")
        return f"Lỗi khi quét email: {e}"


def _format_academic_results(academic_emails, analyze_priority_tool) -> str:
    """Format danh sách email học thuật đã phân nhóm theo ưu tiên."""
    # Phân loại ưu tiên cho từng email
    prioritized: dict[str, list] = {p: [] for p in PRIORITY_ORDER}

    for email in academic_emails:
        try:
            priority = analyze_priority_tool.invoke({
                "subject": email.subject or "",
                "sender": email.sender or "",
                "body": email.body_preview or "",
            })
        except Exception:
            priority = "info"

        if priority not in prioritized:
            priority = "info"
        prioritized[priority].append(email)

    # Build output
    lines = [f"📬 Kết quả quét email học thuật ({len(academic_emails)} email):"]
    lines.append("")

    for priority_key in PRIORITY_ORDER:
        emails_in_group = prioritized[priority_key]
        if not emails_in_group:
            continue

        icon_label = PRIORITY_ICONS[priority_key]
        lines.append(f"{icon_label} ({len(emails_in_group)}):")

        for email in emails_in_group:
            time_str = _format_time(email.received_date_time)
            sender_short = email.sender.split("<")[0].strip() if "<" in email.sender else email.sender
            email_id = email.id
            lines.append(
                f"  • [{email_id}] {sender_short} — \"{email.subject}\" — {time_str}"
            )

        lines.append("")

    lines.append("💡 Bạn muốn tôi tóm tắt chi tiết email nào, hay soạn email trả lời?")
    return "\n".join(lines)


def _format_smart_fallback(non_academic_emails) -> str:
    """Format Smart mode fallback khi không có email học thuật."""
    lines = ["Không có email học thuật mới theo bộ lọc hiện tại."]

    if non_academic_emails:
        recent = non_academic_emails[:SMART_FALLBACK_LIMIT]
        lines.append("")
        lines.append(
            f"Dưới đây là {len(recent)} email gần nhất của bạn, "
            "chưa được xác định là email học thuật:"
        )

        for i, email in enumerate(recent, 1):
            time_str = _format_time(email.received_date_time)
            sender_short = email.sender.split("<")[0].strip() if "<" in email.sender else email.sender
            lines.append(
                f"  {i}. Từ: {sender_short} — \"{email.subject}\" — {time_str}"
            )

        lines.append("")
        lines.append(
            "Bạn có muốn tôi mở rộng tìm kiếm sang tất cả email, "
            "hoặc thêm domain/từ khóa học thuật mới không?"
        )
    else:
        lines.append("")
        lines.append("Hộp thư hiện không có email nào.")

    return "\n".join(lines)
