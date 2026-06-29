"""
tools/note/delete_note.py
-------------------------
LangChain tool to delete a note.
"""

import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger
from db.database import SessionLocal
from db import crud


@tool
def delete_note(note_id: str, config: RunnableConfig = None) -> str:
    """
    Xóa ghi chú học tập.

    Args:
        note_id: ID của ghi chú cần xóa.
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
        success = asyncio.run(service.delete_note(note_id=note_id))
        
        if success:
            return f"✅ Đã xóa ghi chú thành công!"
        else:
            return f"❌ Lỗi: Xóa ghi chú thất bại. Vui lòng kiểm tra lại ID."
    except Exception as e:
        logger.error(f"Error deleting note {note_id} for user={user_id}: {e}")
        return f"Lỗi khi xóa ghi chú: Vui lòng kiểm tra đã liên kết Google chưa. Chi tiết: {e}"
    finally:
        db.close()
