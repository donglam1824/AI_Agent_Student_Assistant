"""
api/v1/documents.py
-------------------
Document management endpoints for RAG:
  - POST   /documents/upload          → Upload + embed file (manual)
  - GET    /documents                 → List user's documents
  - DELETE /documents/{id}            → Delete document

Google Drive endpoints:
  - GET    /documents/drive/folders   → List Drive folders
  - GET    /documents/drive/files     → List Drive files (supported types only)
  - POST   /documents/drive/import    → Import selected Drive files into RAG
  - POST   /documents/drive/sync/{id} → Re-sync 1 Drive file
"""

import os
import shutil
from typing import List, Optional

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


class DriveFolderResponse(BaseModel):
    id: str
    name: str
    parents: List[str] = []


class DriveFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    type_label: str
    modified_time: str
    size: int


class DriveImportRequest(BaseModel):
    file_ids: List[str]


class DriveImportResultItem(BaseModel):
    file_id: str
    file_name: str
    status: str       # "success" | "error"
    num_chunks: int
    error: Optional[str] = None


class DriveSyncResponse(BaseModel):
    status: str       # "updated" | "skipped" | "error"
    num_chunks: int
    message: str


# ── Background Task (Manual Upload) ──────────────────────────────────────

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
        if os.path.exists(file_path):
            os.remove(file_path)


# ── Helper: lấy Google credentials từ user ───────────────────────────────

def _get_user_tokens(user: User, db: Session) -> tuple:
    """Lấy và decrypt Google access + refresh token của user."""
    from db.crud import decrypt_token

    if not user.google_access_token:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản chưa kết nối Google. Vui lòng đăng nhập lại.",
        )
    access_token = decrypt_token(user.google_access_token)
    refresh_token = decrypt_token(user.google_refresh_token) if user.google_refresh_token else ""
    return access_token, refresh_token


# ── Manual Upload Endpoints ────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document for RAG processing."""
    allowed_types = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Loai file khong ho tro. Chi chap nhan: {', '.join(allowed_types.keys())}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    doc = crud.create_document(
        db=db,
        user_id=current_user.id,
        filename=file.filename,
        file_type=allowed_types[ext],
        file_size=file_size,
    )

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
    docs = crud.get_user_documents(db, current_user.id)
    if not any(d.id == doc_id for d in docs):
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai.")

    crud.delete_document(db, doc_id)
    # TODO: Also remove vectors from ChromaDB by metadata filter

    return {"message": "Da xoa tai lieu."}


# ── Google Drive Endpoints ────────────────────────────────────────────────

@router.get("/drive/folders", response_model=List[DriveFolderResponse])
async def list_drive_folders(
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List thu muc tren Google Drive cua nguoi dung.
    Dung parent_id de browse sau vao thu muc con.
    """
    access_token, refresh_token = _get_user_tokens(current_user, db)

    from services.google_drive_service import GoogleDriveService
    try:
        svc = GoogleDriveService(access_token=access_token, refresh_token=refresh_token)
        folders = svc.list_folders(parent_id=parent_id)
    except Exception as e:
        logger.error(f"[/drive/folders] error: {e}")
        raise HTTPException(status_code=502, detail=f"Khong the ket noi Google Drive: {str(e)}")

    return [DriveFolderResponse(id=f.id, name=f.name, parents=f.parents) for f in folders]


@router.get("/drive/files", response_model=List[DriveFileResponse])
async def list_drive_files(
    folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List file duoc ho tro trong Google Drive (hoac trong thu muc cu the).
    Chi tra ve: Google Docs, Sheets, Slides, PDF, DOCX, TXT.
    """
    from config.settings import settings
    access_token, refresh_token = _get_user_tokens(current_user, db)

    from services.google_drive_service import GoogleDriveService
    try:
        svc = GoogleDriveService(access_token=access_token, refresh_token=refresh_token)
        files = svc.list_files(
            folder_id=folder_id,
            max_results=settings.google_drive_max_files,
        )
    except Exception as e:
        logger.error(f"[/drive/files] error: {e}")
        raise HTTPException(status_code=502, detail=f"Khong the liet ke file tu Drive: {str(e)}")

    return [
        DriveFileResponse(
            id=f.id,
            name=f.name,
            mime_type=f.mime_type,
            type_label=f.type_label,
            modified_time=f.modified_time,
            size=f.size,
        )
        for f in files
    ]


@router.post("/drive/import", response_model=List[DriveImportResultItem])
async def import_drive_files(
    body: DriveImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import mot hoac nhieu file tu Google Drive vao he thong RAG.
    Xu ly dong bo - tra ve ket qua sau khi hoan thanh.
    """
    if not body.file_ids:
        raise HTTPException(status_code=400, detail="Danh sach file_ids khong duoc rong.")

    from config.settings import settings
    if len(body.file_ids) > settings.google_drive_max_files:
        raise HTTPException(
            status_code=400,
            detail=f"Khong the import qua {settings.google_drive_max_files} file cung luc.",
        )

    access_token, refresh_token = _get_user_tokens(current_user, db)

    from services.doc_search_service import get_doc_search_service
    svc = get_doc_search_service()

    try:
        results = svc.import_from_drive(
            file_ids=body.file_ids,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception as e:
        logger.error(f"[/drive/import] error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi import tu Drive: {str(e)}")

    return [
        DriveImportResultItem(
            file_id=r["file_id"],
            file_name=r["file_name"],
            status=r["status"],
            num_chunks=r["num_chunks"],
            error=r.get("error"),
        )
        for r in results
    ]


@router.post("/drive/sync/{file_id}", response_model=DriveSyncResponse)
async def sync_drive_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Re-sync mot file Drive da import.
    Kiem tra modifiedTime - neu chua thay doi thi bo qua (tra ve 'skipped').
    """
    access_token, refresh_token = _get_user_tokens(current_user, db)

    from services.doc_search_service import get_doc_search_service
    svc = get_doc_search_service()

    try:
        result = svc.sync_drive_document(
            file_id=file_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception as e:
        logger.error(f"[/drive/sync/{file_id}] error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi sync file Drive: {str(e)}")

    return DriveSyncResponse(
        status=result["status"],
        num_chunks=result["num_chunks"],
        message=result["message"],
    )
