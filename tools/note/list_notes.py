"""
tools/note/list_notes.py
------------------------
LangChain tool to list notes.
"""

import asyncio
from langchain_core.tools import tool
from services.graph_note_service import get_note_service
from core.logger import logger

@tool
def list_notes(limit: int = 5) -> str:
    """
    Get the most recent notes from the user's notebook.
    
    Args:
        limit: Number of notes to retrieve (default: 5)
    """
    service = get_note_service()
    try:
        notes = asyncio.run(service.list_notes(limit=limit))
        if not notes:
            return "Không có ghi chú nào."
        
        lines = [f"📝 Danh sách {len(notes)} ghi chú gần đây:"]
        for n in notes:
            lines.append(f"  • [{n.id}] {n.title}\n    Nội dung: {n.content}\n    Cập nhật: {n.created_at}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error listing notes: {e}")
        return f"Lỗi khi lấy ghi chú: {e}"
