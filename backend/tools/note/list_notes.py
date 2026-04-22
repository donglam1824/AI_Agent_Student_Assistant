"""
tools/note/list_notes.py
------------------------
LangChain tool to list notes from SQLite (local storage).
"""

from langchain_core.tools import tool
from core.logger import logger


@tool
def list_notes(limit: int = 5) -> str:
    """
    Xem các ghi chú học tập gần đây của sinh viên.

    Args:
        limit: Số ghi chú muốn xem (mặc định 5)
    """
    from db.database import SessionLocal
    from db import crud

    db = SessionLocal()
    try:
        # Dùng user mặc định cho CLI / agent mode;
        # trong API mode, user_id được truyền qua endpoint.
        notes = crud.get_user_notes(db, user_id="default", limit=limit)
        if not notes:
            return "Chưa có ghi chú nào. Bạn có thể nhờ mình tạo ghi chú mới."

        lines = [f"📝 Danh sách {len(notes)} ghi chú gần đây:"]
        for n in notes:
            updated = n.updated_at.strftime("%d/%m/%Y %H:%M") if n.updated_at else ""
            lines.append(
                f"  • [{n.id[:8]}] {n.title}\n"
                f"    Nội dung: {n.content[:80]}{'...' if len(n.content) > 80 else ''}\n"
                f"    Cập nhật: {updated}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing notes: {e}")
        return f"Lỗi khi lấy ghi chú: {e}"
    finally:
        db.close()
