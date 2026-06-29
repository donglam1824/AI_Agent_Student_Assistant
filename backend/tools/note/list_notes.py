"""
tools/note/list_notes.py
------------------------
LangChain tool to list notes.
"""

import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger
from db.database import SessionLocal
from db import crud


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

    db = SessionLocal()
    try:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            return "❌ Lỗi: Người dùng không tồn tại."

        from services.base_note_service import get_note_service
        service = get_note_service(user)
        notes = asyncio.run(service.list_notes(limit=limit))
        if not notes:
            return "Không có ghi chú nào. Bạn có muốn tạo ghi chú mới không?"

        lines = [f"📝 Danh sách {len(notes)} ghi chú:"]
        for n in notes:
            content_preview = n.content[:80] if n.content else "(không có nội dung)"
            lines.append(
                f"  • [{n.id[:8]}] {n.title}\n"
                f"    {content_preview}{'...' if len(n.content) > 80 else ''}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing notes for user={user_id}: {e}")
        return f"Lỗi khi lấy ghi chú: Vui lòng kiểm tra đã liên kết Google chưa. Chi tiết: {e}"
    finally:
        db.close()
