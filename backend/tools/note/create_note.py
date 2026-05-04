"""
tools/note/create_note.py
-------------------------
LangChain tool to create a note via Google Tasks (ORCA Notes).
Nhận user_id qua LangChain RunnableConfig.
"""

import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from core.logger import logger


@tool
def create_note(title: str, content: str, config: RunnableConfig = None) -> str:
    """
    Tạo ghi chú học tập mới cho sinh viên.

    Args:
        title: Tiêu đề ghi chú (ví dụ: "Bài tập Toán chương 5")
        content: Nội dung ghi chú
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return "❌ Lỗi: Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại."

    from services.google_note_service import GoogleNoteService
    service = GoogleNoteService(user_id=user_id)
    try:
        note = asyncio.run(service.create_note(title=title, content=content))
        return (
            f"✅ Đã tạo ghi chú thành công!\n"
            f"  📝 Tiêu đề: {note['title']}\n"
            f"  📄 Nội dung: {note['content'][:100]}{'...' if len(note['content']) > 100 else ''}\n"
            f"  🔗 ID: {note['id'][:12]}..."
        )
    except Exception as e:
        logger.error(f"Error creating note for user={user_id}: {e}")
        return f"Lỗi khi tạo ghi chú: {e}"
