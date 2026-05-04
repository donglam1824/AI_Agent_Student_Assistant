"""
tools/note/list_notes.py
------------------------
LangChain tool to list notes from Google Tasks (ORCA Notes).
Nhận user_id qua LangChain RunnableConfig.
"""

import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger


@tool
def list_notes(limit: int = 10, config: RunnableConfig = None) -> str:
    """
    Liệt kê các ghi chú học tập gần đây của người dùng.

    Args:
        limit: Số ghi chú cần lấy (mặc định 10).
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_note_service import GoogleNoteService
    service = GoogleNoteService(user_id=user_id)
    try:
        notes = asyncio.run(service.list_notes(limit=limit))
        if not notes:
            return "Không có ghi chú nào. Bạn có muốn tạo ghi chú mới không?"

        lines = [f"📝 Danh sách {len(notes)} ghi chú:"]
        for n in notes:
            content_preview = n["content"][:80] if n["content"] else "(không có nội dung)"
            lines.append(
                f"  • [{n['id'][:8]}] {n['title']}\n"
                f"    {content_preview}{'...' if len(n['content']) > 80 else ''}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing notes for user={user_id}: {e}")
        return f"Lỗi khi lấy ghi chú: {e}"
