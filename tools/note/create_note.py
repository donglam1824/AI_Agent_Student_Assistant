"""
tools/note/create_note.py
-------------------------
LangChain tool to create a note.
"""

import asyncio
from langchain_core.tools import tool
from services.graph_note_service import get_note_service
from models.note import NoteCreate
from core.logger import logger

@tool
def create_note(title: str, content: str) -> str:
    """
    Create a new note.
    
    Args:
        title: Title of the note
        content: Content of the note
    """
    service = get_note_service()
    data = NoteCreate(title=title, content=content)
    try:
        note = asyncio.run(service.create_note(data))
        return f"Đã tạo ghi chú '{note.title}' thành công."
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        return f"Lỗi khi tạo ghi chú: {e}"
