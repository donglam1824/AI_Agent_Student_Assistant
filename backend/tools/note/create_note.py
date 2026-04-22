"""
tools/note/create_note.py
-------------------------
LangChain tool to create a note in SQLite (local storage).
"""

from langchain_core.tools import tool
from core.logger import logger


@tool
def create_note(title: str, content: str) -> str:
    """
    Tạo ghi chú học tập mới cho sinh viên.

    Args:
        title: Tiêu đề ghi chú (ví dụ: "Bài tập Toán chương 5")
        content: Nội dung ghi chú
    """
    from db.database import SessionLocal
    from db import crud

    db = SessionLocal()
    try:
        note = crud.create_note(db, user_id="default", title=title, content=content)
        return (
            f"✅ Đã tạo ghi chú thành công!\n"
            f"  📝 Tiêu đề: {note.title}\n"
            f"  📄 Nội dung: {note.content[:100]}{'...' if len(note.content) > 100 else ''}\n"
            f"  🕐 Lúc: {note.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        return f"Lỗi khi tạo ghi chú: {e}"
    finally:
        db.close()
