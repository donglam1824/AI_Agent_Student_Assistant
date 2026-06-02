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
import hashlib
import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import User, Document
from api.deps import get_current_user
from core.logger import logger

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


def _hash_file(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_wiki_key(doc: Document) -> str:
    """Stable key used by the Markdown wiki manifest."""
    if doc.source_type in {"google_drive", "onedrive"} and doc.drive_file_id:
        return f"{doc.source_type}:{doc.drive_file_id}"
    return doc.id


def _document_response(doc: Document, tags: Optional[List[str]] = None) -> "DocumentResponse":
    if tags is None:
        try:
            tags = json.loads(doc.tags) if doc.tags else []
        except Exception:
            tags = []
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        error_message=doc.error_message,
        topic=doc.topic,
        category=doc.category,
        tags=tags,
        source_type=doc.source_type,
        created_at=doc.created_at.isoformat(),
    )


# ── Response Models ───────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    topic: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source_type: Optional[str] = None
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

def _process_document(doc_id: str, file_path: str, db_url: str, user_id: str):
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
        from services.topic_classifier import TopicClassifier
        import json

        doc = (
            db.query(Document)
            .filter(Document.id == doc_id, Document.user_id == user_id)
            .first()
        )
        display_source = doc.filename if doc else os.path.basename(file_path)
        content_hash = doc.content_hash if doc and doc.content_hash else ""

        chunks = load_document(
            file_path,
            metadata={
                "doc_id": doc_id,
                "user_id": user_id,
                "source": display_source,
                "source_type": "manual_upload",
                "content_hash": content_hash,
            },
        )
        if not chunks:
            crud.update_document_status(db, doc_id, "error", error_message="Không thể đọc nội dung file.")
            return

        # Phân loại chủ đề bằng Gemini
        text_sample = "\n".join([c.page_content for c in chunks[:2]]) if chunks else ""
        classification = TopicClassifier.classify(text_sample)
        topic = classification["topic"]
        category = classification["category"]
        tags_list = classification["tags"]
        tags_str = json.dumps(tags_list, ensure_ascii=False)

        for chunk in chunks:
            chunk.metadata.update({
                "doc_id": doc_id,
                "user_id": user_id,
                "source": display_source,
                "topic": topic,
                "category": category,
                "tags": tags_str,
                "content_hash": content_hash,
            })

        try:
            from services.wiki_service import get_wiki_service

            wiki_service = get_wiki_service()
            wiki_result = wiki_service.upsert_document(
                user_id=user_id,
                document_key=doc_id,
                title=display_source,
                chunks=chunks,
                topic=topic,
                category=category,
                tags=tags_list,
                source_type="manual_upload",
                source_id=doc_id,
            )
            wiki_service.contextualize_chunks(
                chunks=chunks,
                title=display_source,
                topic=topic,
                category=category,
                tags=tags_list,
                wiki_path=wiki_result.relative_document_path,
                summary=wiki_result.summary,
            )
        except Exception as wiki_error:
            logger.error(f"Document wiki update error for {doc_id}: {wiki_error}")

        vector_store = get_vector_store()
        vector_store.add_documents(chunks)

        crud.update_document_status(db, doc_id, "ready", chunk_count=len(chunks))
        crud.update_document_topic(db, doc_id, topic, category, tags_list)
        logger.info(f"Document {doc_id} processed: {len(chunks)} chunks, topic={topic}, category={category}")

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
    from core.crypto import decrypt_token

    if not user.google_access_token:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản chưa kết nối Google. Vui lòng đăng nhập lại.",
        )
    access_token = decrypt_token(user.google_access_token)
    refresh_token = decrypt_token(user.google_refresh_token) if user.google_refresh_token else ""
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="Khong the giai ma Google token. Vui long dang nhap lai.",
        )
    return access_token, refresh_token


def _get_user_microsoft_token(user: User, db: Session) -> str:
    """Get a refreshed delegated Microsoft Graph access token for the current user."""
    try:
        from services.microsoft_oauth_service import get_user_microsoft_access_token

        access_token = get_user_microsoft_access_token(db, user.id)
    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"Tai khoan chua ket noi Microsoft hoac token khong hop le: {str(e)}",
        )
    if not access_token:
        raise HTTPException(
            status_code=403,
            detail="Khong the lay Microsoft access token. Vui long ket noi lai Microsoft.",
        )
    return access_token


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
    safe_filename = os.path.basename(file.filename or "")
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Loai file khong ho tro. Chi chap nhan: {', '.join(allowed_types.keys())}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{uuid.uuid4().hex}_{safe_filename}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)
    content_hash = _hash_file(file_path)

    existing_doc = crud.get_user_document_by_hash(
        db,
        current_user.id,
        content_hash,
        statuses=["processing", "ready"],
    )
    if existing_doc:
        os.remove(file_path)
        logger.info(
            f"Upload skipped duplicate file for user={current_user.id}: "
            f"{safe_filename} matches document {existing_doc.id}"
        )
        return _document_response(existing_doc)

    doc = crud.create_document(
        db=db,
        user_id=current_user.id,
        filename=safe_filename,
        file_type=allowed_types[ext],
        file_size=file_size,
        content_hash=content_hash,
    )

    from db.database import DATABASE_URL
    background_tasks.add_task(_process_document, doc.id, file_path, DATABASE_URL, current_user.id)

    return _document_response(doc, tags=[])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for the current user."""
    import json
    docs = crud.get_user_documents(db, current_user.id)
    response = []
    for d in docs:
        tags_parsed = []
        if d.tags:
            try:
                tags_parsed = json.loads(d.tags)
            except Exception:
                tags_parsed = []
        response.append(
            DocumentResponse(
                id=d.id,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                chunk_count=d.chunk_count,
                status=d.status,
                error_message=d.error_message,
                topic=d.topic,
                category=d.category,
                tags=tags_parsed,
                source_type=d.source_type,
                created_at=d.created_at.isoformat(),
            )
        )
    return response


@router.get("/topics")
async def get_document_topics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy thống kê số lượng tài liệu theo danh mục và chủ đề."""
    summary = crud.get_topic_summary(db, current_user.id)
    return summary


class UpdateDocumentTopicRequest(BaseModel):
    topic: str
    category: str
    tags: List[str]


@router.put("/{doc_id}/topic", response_model=DocumentResponse)
async def update_document_topic(
    doc_id: str,
    body: UpdateDocumentTopicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cho phép người dùng tự chỉnh sửa chủ đề, danh mục và tags của tài liệu."""
    docs = crud.get_user_documents(db, current_user.id)
    doc_to_edit = None
    for d in docs:
        if d.id == doc_id:
            doc_to_edit = d
            break
            
    if not doc_to_edit:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại hoặc không thuộc quyền sở hữu của bạn.")
        
    import json
    # Cập nhật trong DB
    updated_doc = crud.update_document_topic(db, doc_id, body.topic, body.category, body.tags)
    
    tags_parsed = []
    if updated_doc.tags:
        try:
            tags_parsed = json.loads(updated_doc.tags)
        except Exception:
            tags_parsed = []
            
    return DocumentResponse(
        id=updated_doc.id,
        filename=updated_doc.filename,
        file_type=updated_doc.file_type,
        file_size=updated_doc.file_size,
        chunk_count=updated_doc.chunk_count,
        status=updated_doc.status,
        error_message=updated_doc.error_message,
        topic=updated_doc.topic,
        category=updated_doc.category,
        tags=tags_parsed,
        source_type=updated_doc.source_type,
        created_at=updated_doc.created_at.isoformat(),
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and its embeddings."""
    docs = crud.get_user_documents(db, current_user.id)
    doc_to_delete = next((d for d in docs if d.id == doc_id), None)
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Tai lieu khong ton tai.")

    try:
        from rag.vector_store import delete_vectors_by_metadata

        if doc_to_delete.source_type in {"google_drive", "onedrive"} and doc_to_delete.drive_file_id:
            vector_filter = {
                "$and": [
                    {"drive_file_id": doc_to_delete.drive_file_id},
                    {"source_type": doc_to_delete.source_type},
                    {"user_id": current_user.id},
                ]
            }
        else:
            vector_filter = {"doc_id": doc_id}
        delete_vectors_by_metadata(vector_filter)
    except Exception as e:
        logger.error(f"Delete document vectors error: {e}")
        raise HTTPException(status_code=500, detail=f"Khong the xoa vector cua tai lieu: {str(e)}")

    try:
        from services.wiki_service import get_wiki_service

        get_wiki_service().remove_document(
            user_id=current_user.id,
            document_key=_document_wiki_key(doc_to_delete),
        )
    except Exception as e:
        logger.error(f"Delete document wiki error: {e}")

    crud.delete_document(db, doc_id)

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
            user_id=current_user.id,
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
            user_id=current_user.id,
        )
    except Exception as e:
        logger.error(f"[/drive/sync/{file_id}] error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi sync file Drive: {str(e)}")

    return DriveSyncResponse(
        status=result["status"],
        num_chunks=result["num_chunks"],
        message=result["message"],
    )


@router.get("/onedrive/folders", response_model=List[DriveFolderResponse])
async def list_onedrive_folders(
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List folders from the connected user's OneDrive."""
    access_token = _get_user_microsoft_token(current_user, db)

    from services.onedrive_service import OneDriveService
    try:
        svc = OneDriveService(access_token=access_token)
        folders = svc.list_folders(parent_id=parent_id)
    except Exception as e:
        logger.error(f"[/onedrive/folders] error: {e}")
        raise HTTPException(status_code=502, detail=f"Khong the ket noi OneDrive: {str(e)}")

    return [DriveFolderResponse(id=f.id, name=f.name, parents=f.parents) for f in folders]


@router.get("/onedrive/files", response_model=List[DriveFileResponse])
async def list_onedrive_files(
    folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List supported files from the connected user's OneDrive."""
    from config.settings import settings
    access_token = _get_user_microsoft_token(current_user, db)

    from services.onedrive_service import OneDriveService
    try:
        svc = OneDriveService(access_token=access_token)
        files = svc.list_files(
            folder_id=folder_id,
            max_results=settings.google_drive_max_files,
        )
    except Exception as e:
        logger.error(f"[/onedrive/files] error: {e}")
        raise HTTPException(status_code=502, detail=f"Khong the liet ke file tu OneDrive: {str(e)}")

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


@router.post("/onedrive/import", response_model=List[DriveImportResultItem])
async def import_onedrive_files(
    body: DriveImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import selected OneDrive files into RAG."""
    if not body.file_ids:
        raise HTTPException(status_code=400, detail="Danh sach file_ids khong duoc rong.")

    from config.settings import settings
    if len(body.file_ids) > settings.google_drive_max_files:
        raise HTTPException(
            status_code=400,
            detail=f"Khong the import qua {settings.google_drive_max_files} file cung luc.",
        )

    access_token = _get_user_microsoft_token(current_user, db)

    from services.doc_search_service import get_doc_search_service
    svc = get_doc_search_service()

    try:
        results = svc.import_from_onedrive(
            file_ids=body.file_ids,
            access_token=access_token,
            user_id=current_user.id,
        )
    except Exception as e:
        logger.error(f"[/onedrive/import] error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi import tu OneDrive: {str(e)}")

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


@router.post("/onedrive/sync/{file_id}", response_model=DriveSyncResponse)
async def sync_onedrive_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-sync a OneDrive file already imported into RAG."""
    access_token = _get_user_microsoft_token(current_user, db)

    from services.doc_search_service import get_doc_search_service
    svc = get_doc_search_service()

    try:
        result = svc.sync_onedrive_document(
            file_id=file_id,
            access_token=access_token,
            user_id=current_user.id,
        )
    except Exception as e:
        logger.error(f"[/onedrive/sync/{file_id}] error: {e}")
        raise HTTPException(status_code=500, detail=f"Loi sync file OneDrive: {str(e)}")

    return DriveSyncResponse(
        status=result["status"],
        num_chunks=result["num_chunks"],
        message=result["message"],
    )
