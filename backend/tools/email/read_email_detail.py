"""
tools/email/read_email_detail.py
---------------------------------
LangChain tool: đọc chi tiết một email cụ thể theo ID.
Tóm tắt nội dung bằng LLM, trích xuất deadline, phân loại ưu tiên.
"""

import asyncio
import json

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.logger import logger


PRIORITY_LABELS = {
    "urgent": "🔴 Khẩn cấp",
    "important": "🟡 Quan trọng",
    "follow_up": "🔵 Cần phản hồi",
    "info": "🟢 Thông tin",
}


def _format_received_time(received_date_time: str) -> str:
    """Format thời gian nhận email để hiển thị."""
    if not received_date_time:
        return "Không rõ"

    from datetime import datetime

    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(
                received_date_time.split("+")[0].split(".")[0],
                fmt.split("+")[0].split(".")[0],
            )
            return dt.strftime("%H:%M %d/%m/%Y")
        except ValueError:
            continue

    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(received_date_time)
        return dt.strftime("%H:%M %d/%m/%Y")
    except Exception:
        pass

    return received_date_time


@tool
def read_email_detail(message_id: str, config: RunnableConfig = None) -> str:
    """
    Đọc chi tiết một email cụ thể: lấy nội dung đầy đủ, tóm tắt bằng AI,
    trích xuất deadline và phân loại ưu tiên.

    Args:
        message_id: ID của email (có thể dạng "gmail:<id>" hoặc "outlook:<id>").
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.graph_email_service import get_email_service
    from agents.email.tools.analyze_priority import analyze_priority
    from agents.email.tools.extract_deadline import extract_deadline
    from core.llm_manager import llm_manager

    try:
        # 1. Xác định nguồn email và lấy nội dung
        source, raw_id = _parse_message_id(message_id)
        email_data = _fetch_full_email(user_id, raw_id, source)

        if not email_data:
            return f"Không tìm thấy email với ID: {message_id}"

        sender = email_data.get("sender", "Không rõ")
        subject = email_data.get("subject", "(Không có tiêu đề)")
        body = email_data.get("body", "")
        snippet = email_data.get("snippet", "")
        received_time = email_data.get("received_date_time", "")

        # 2. Phân loại ưu tiên (rule-based, nhanh)
        priority = analyze_priority.invoke({
            "subject": subject,
            "sender": sender,
            "body": body or snippet,
        })
        priority_label = PRIORITY_LABELS.get(priority, "🟢 Thông tin")

        # 3. Tóm tắt nội dung bằng LLM
        content_for_summary = body if body else snippet
        summary_text = _summarize_email(
            llm_manager, subject, sender, content_for_summary
        )

        # 4. Trích xuất deadline
        deadline_text = ""
        action_suggestions = []

        if body or snippet:
            try:
                deadline_result_str = extract_deadline.invoke({
                    "text": body or snippet,
                })
                deadline_info = json.loads(deadline_result_str)

                if deadline_info.get("has_deadline") and deadline_info.get("deadline_date"):
                    date_str = deadline_info["deadline_date"]
                    time_str = deadline_info.get("deadline_time", "")
                    task_name = deadline_info.get("task_name", subject)
                    deadline_display = f"{date_str} {time_str}".strip()
                    deadline_text = f"\n⏰ Deadline: {deadline_display} — \"{task_name}\""
                    action_suggestions.append(
                        "Tạo nhắc lịch cho deadline này"
                    )
            except Exception as e:
                logger.warning(f"Error extracting deadline: {e}")

        # Gợi ý hành động
        if priority in ("follow_up", "urgent"):
            action_suggestions.append("Soạn email phản hồi")

        # 5. Format kết quả
        lines = [
            "📧 Chi tiết email:",
            f"  • Từ: {sender}",
            f"  • Tiêu đề: {subject}",
            f"  • Nhận lúc: {_format_received_time(received_time)}",
            f"  • Ưu tiên: {priority_label}",
            "",
            "📝 Tóm tắt:",
            summary_text,
        ]

        if deadline_text:
            lines.append(deadline_text)

        if action_suggestions:
            lines.append("")
            suggestions = " hay ".join(
                f"**{s.lower()}**" for s in action_suggestions
            )
            lines.append(f"💡 Bạn muốn tôi {suggestions}?")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error reading email detail for user={user_id}: {e}")
        return f"Lỗi khi đọc chi tiết email: {e}"


def _parse_message_id(message_id: str) -> tuple[str, str]:
    """Parse message_id dạng 'gmail:<id>' hoặc 'outlook:<id>' thành (source, raw_id)."""
    if ":" in message_id:
        parts = message_id.split(":", 1)
        return parts[0].lower(), parts[1]
    # Mặc định là gmail nếu không có prefix
    return "gmail", message_id


def _fetch_full_email(user_id: str, raw_id: str, source: str) -> dict | None:
    """Lấy nội dung đầy đủ của email từ service tương ứng."""
    try:
        if source == "gmail":
            from services.google_email_service import GoogleEmailService
            service = GoogleEmailService(user_id=user_id)
            gmail_service = service._service

            msg_data = gmail_service.users().messages().get(
                userId="me", id=raw_id, format="full"
            ).execute()

            headers = msg_data.get("payload", {}).get("headers", [])
            header_map = {
                h["name"].lower(): h["value"] for h in headers
            }

            # Extract body
            import base64

            def get_body(part):
                body_text = ""
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data")
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode("utf-8")
                elif "parts" in part:
                    for p in part["parts"]:
                        body_text += get_body(p)
                return body_text

            payload = msg_data.get("payload", {})
            body = get_body(payload)
            if not body and payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(
                    payload["body"]["data"]
                ).decode("utf-8")

            return {
                "sender": header_map.get("from", "unknown"),
                "subject": header_map.get("subject", "(Không có tiêu đề)"),
                "body": body,
                "snippet": msg_data.get("snippet", ""),
                "received_date_time": header_map.get("date", ""),
            }

        elif source == "outlook":
            import requests
            from db.database import SessionLocal
            from services.microsoft_oauth_service import get_user_microsoft_access_token

            db = SessionLocal()
            try:
                token = get_user_microsoft_access_token(db, user_id)
                if not token:
                    return None

                response = requests.get(
                    f"https://graph.microsoft.com/v1.0/me/messages/{raw_id}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                    timeout=30,
                )
                if response.status_code >= 400:
                    logger.error(f"Outlook fetch failed: {response.status_code}")
                    return None

                data = response.json()
                sender_info = (data.get("sender") or {}).get("emailAddress") or {}
                sender_name = sender_info.get("name", "")
                sender_addr = sender_info.get("address", "unknown")
                sender = f"{sender_name} <{sender_addr}>" if sender_name else sender_addr

                # Body from Outlook is HTML by default, try to get text
                body_content = (data.get("body") or {}).get("content", "")

                return {
                    "sender": sender,
                    "subject": data.get("subject", "(Không có tiêu đề)"),
                    "body": body_content,
                    "snippet": data.get("bodyPreview", ""),
                    "received_date_time": data.get("receivedDateTime", ""),
                }
            finally:
                db.close()

        return None

    except Exception as e:
        logger.error(f"Error fetching full email {source}:{raw_id}: {e}")
        return None


def _summarize_email(llm_manager, subject: str, sender: str, content: str) -> str:
    """Tóm tắt nội dung email bằng LLM."""
    if not content or len(content.strip()) < 20:
        return "Nội dung email quá ngắn hoặc trống."

    try:
        llm = llm_manager.get_model(task="email_summary")
        # Giới hạn content gửi tới LLM để tránh quá dài
        truncated = content[:2000] if len(content) > 2000 else content

        prompt = (
            "Tóm tắt email sau trong 2-3 câu ngắn gọn bằng tiếng Việt. "
            "Tập trung vào nội dung chính, hành động cần làm (nếu có), "
            "và thông tin quan trọng cho sinh viên.\n\n"
            f"Chủ đề: {subject}\n"
            f"Người gửi: {sender}\n"
            f"Nội dung:\n{truncated}"
        )

        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.warning(f"Error summarizing email: {e}")
        return content[:200] + "..." if len(content) > 200 else content
