from abc import ABC, abstractmethod
from typing import List, Optional
from models.note import NoteItem

class BaseNoteService(ABC):
    """
    Interface for Note Services.
    """
    
    @abstractmethod
    async def list_notes(self, limit: int = 20) -> List[NoteItem]:
        """Lấy danh sách ghi chú."""
        pass

    @abstractmethod
    async def create_note(self, title: str, content: str = "") -> NoteItem:
        """Tạo ghi chú mới."""
        pass

    @abstractmethod
    async def update_note(self, note_id: str, title: Optional[str] = None, content: Optional[str] = None) -> NoteItem:
        """Cập nhật ghi chú."""
        pass

    @abstractmethod
    async def delete_note(self, note_id: str) -> bool:
        """Xóa ghi chú."""
        pass

def get_note_service(user) -> BaseNoteService:
    """Factory để lấy Note Service."""
    # Hiện tại mặc định sử dụng Google Tasks (Phương án 1)
    from services.google_note_service import GoogleNoteService
    return GoogleNoteService(user_id=user.id)
