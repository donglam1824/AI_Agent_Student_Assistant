"""
api/v1/notes.py
---------------
Note management endpoints:
  - GET    /notes        → List user's notes
  - POST   /notes        → Create a new note
  - PUT    /notes/{id}   → Update a note
  - DELETE /notes/{id}   → Delete a note
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from api.deps import get_current_user
from core.logger import logger
from services.base_note_service import get_note_service
from models.note import NoteItem

router = APIRouter(prefix="/notes", tags=["Notes"])


# ── Request Models ────────────────────────────────────────────────────────

class NoteCreateRequest(BaseModel):
    title: str
    content: str = ""


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[NoteItem])
async def list_notes(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    """List all notes for the current user from Google Tasks."""
    try:
        service = get_note_service(current_user)
        return await service.list_notes(limit=limit)
    except ValueError as e:
        logger.error(f"Credential error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng liên kết tài khoản Google để sử dụng tính năng ghi chú."
        )
    except Exception as e:
        logger.error(f"Error listing notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=NoteItem, status_code=201)
async def create_note(
    body: NoteCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new note in Google Tasks."""
    try:
        service = get_note_service(current_user)
        return await service.create_note(title=body.title, content=body.content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng liên kết tài khoản Google để sử dụng tính năng ghi chú."
        )
    except Exception as e:
        logger.error(f"Error creating note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{note_id}", response_model=NoteItem)
async def update_note(
    note_id: str,
    body: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Update a note in Google Tasks."""
    try:
        service = get_note_service(current_user)
        return await service.update_note(note_id, title=body.title, content=body.content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng liên kết tài khoản Google để sử dụng tính năng ghi chú."
        )
    except Exception as e:
        logger.error(f"Error updating note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a note in Google Tasks."""
    try:
        service = get_note_service(current_user)
        success = await service.delete_note(note_id)
        if not success:
            raise HTTPException(status_code=400, detail="Xóa ghi chú thất bại.")
        return {"message": "Đã xóa ghi chú."}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng liên kết tài khoản Google để sử dụng tính năng ghi chú."
        )
    except Exception as e:
        logger.error(f"Error deleting note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
