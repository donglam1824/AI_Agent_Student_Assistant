"""
models/note.py
--------------
Pydantic schemas for Note.
"""

from typing import Optional
from pydantic import BaseModel, Field

class NoteCreate(BaseModel):
    """Input model for creating a new note."""
    title: str = Field(..., description="Title of the note")
    content: str = Field(..., description="Content of the note")

class NoteUpdate(BaseModel):
    """Input model for updating an existing note."""
    title: Optional[str] = None
    content: Optional[str] = None

class NoteItem(BaseModel):
    """Output model representing a note."""
    id: str = Field(..., description="Note ID")
    title: str
    content: str
    created_at: str
    
    class Config:
        from_attributes = True
