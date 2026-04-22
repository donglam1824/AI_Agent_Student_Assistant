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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import User
from api.deps import get_current_user
from core.logger import logger

router = APIRouter(prefix="/notes", tags=["Notes"])


# ── Request / Response Models ─────────────────────────────────────────────

class NoteCreateRequest(BaseModel):
    title: str
    content: str = ""


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[NoteResponse])
async def list_notes(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all notes for the current user."""
    notes = crud.get_user_notes(db, current_user.id, limit=limit)
    return [
        NoteResponse(
            id=n.id,
            title=n.title,
            content=n.content,
            created_at=n.created_at.isoformat(),
            updated_at=n.updated_at.isoformat(),
        )
        for n in notes
    ]


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(
    body: NoteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new note."""
    note = crud.create_note(db, user_id=current_user.id, title=body.title, content=body.content)
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    body: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a note."""
    note = crud.get_note_by_id(db, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ghi chú không tồn tại.")

    updated = crud.update_note(db, note_id, title=body.title, content=body.content)
    return NoteResponse(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a note."""
    note = crud.get_note_by_id(db, note_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ghi chú không tồn tại.")

    crud.delete_note(db, note_id)
    return {"message": "Đã xóa ghi chú."}
