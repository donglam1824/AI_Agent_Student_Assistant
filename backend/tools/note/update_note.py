"""
tools/note/update_note.py
-------------------------
LangChain tool to update a note.
"""

import asyncio
from typing import Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger
from db.database import SessionLocal
from db import crud


@tool
def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None, config: RunnableConfig = None) -> str:
    """
    Sửa ghi chú học tập.

    Args:
        note_id: ID của ghi chú cần sửa.
        title: Tiêu đề ghi chú mới (tùy chọn).
        content: Nội dung ghi chú mới (tùy chọn).
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
        note = asyncio.run(service.update_note(note_id=note_id, title=title, content=content))
        
        return (
            f"✅ Đã cập nhật ghi chú thành công!\n"
            f"  📝 Tiêu đề: {note.title}\n"
            f"  📄 Nội dung: {note.content[:100]}{'...' if len(note.content) > 100 else ''}\n"
            f"  🔗 ID: {note.id[:12]}..."
        )
    except Exception as e:
        logger.error(f"Error updating note {note_id} for user={user_id}: {e}")
        return f"Lỗi khi sửa ghi chú: Vui lòng kiểm tra đã liên kết Google chưa. Chi tiết: {e}"
    finally:
        db.close()
