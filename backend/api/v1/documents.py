"""
api/v1/documents.py
-------------------
Document management endpoints for RAG:
  - POST   /documents/upload  → Upload + embed file
  - GET    /documents         → List user's documents
  - DELETE /documents/{id}    → Delete document
"""

import os
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import User
from api.deps import get_current_user
from core.logger import logger

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


# ── Response Models ───────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    created_at: str


# ── Background Task ──────────────────────────────────────────────────────

def _process_document(doc_id: str, file_path: str, db_url: str):
    """
    Background task: parse → chunk → embed → store in ChromaDB.
    Updates document status in DB when done.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    DBSession = sessionmaker(bind=db_engine)
    db = DBSession()

    try:
        # Use existing RAG pipeline
        from rag.document_loader import load_document
        from rag.vector_store import get_vector_store

        chunks = load_document(file_path)
        if not chunks:
            crud.update_document_status(db, doc_id, "error", error_message="Không thể đọc nội dung file.")
            return

        vector_store = get_vector_store()
        vector_store.add_documents(chunks)

        crud.update_document_status(db, doc_id, "ready", chunk_count=len(chunks))
        logger.info(f"Document {doc_id} processed: {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Document processing error: {e}")
        crud.update_document_status(db, doc_id, "error", error_message=str(e))
    finally:
        db.close()
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document for RAG processing."""
    # Validate file type
    allowed_types = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Loại file không hỗ trợ. Chỉ chấp nhận: {', '.join(allowed_types.keys())}",
        )

    # Save file to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    # Create document record
    doc = crud.create_document(
        db=db,
        user_id=current_user.id,
        filename=file.filename,
        file_type=allowed_types[ext],
        file_size=file_size,
    )

    # Process in background
    from db.database import DATABASE_URL
    background_tasks.add_task(_process_document, doc.id, file_path, DATABASE_URL)

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        created_at=doc.created_at.isoformat(),
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for the current user."""
    docs = crud.get_user_documents(db, current_user.id)
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size,
            chunk_count=d.chunk_count,
            status=d.status,
            error_message=d.error_message,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and its embeddings."""
    # Verify ownership
    docs = crud.get_user_documents(db, current_user.id)
    if not any(d.id == doc_id for d in docs):
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại.")

    crud.delete_document(db, doc_id)
    # TODO: Also remove vectors from ChromaDB

    return {"message": "Đã xóa tài liệu."}
