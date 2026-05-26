"""
services/doc_search_service.py
-------------------------------
DocSearchService: orchestrate upload và search,
quản lý metadata tài liệu trong SQLite thông qua SQLAlchemy.

Hỗ trợ 2 nguồn tài liệu:
  1. Manual upload (PDF, DOCX, TXT từ giao diện web)
  2. Google Drive & OneDrive (import file đã chọn hoặc sync lại)
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
import uuid

from rag.document_loader import DocumentLoader
from rag.vector_store import get_vector_store
from rag.retriever import Retriever
from core.logger import logger
from db.database import SessionLocal
from db.models import Document
from services.topic_classifier import TopicClassifier

# Source type constants
SOURCE_MANUAL = "manual_upload"
SOURCE_DRIVE = "google_drive"
SOURCE_ONEDRIVE = "onedrive"


class DocSearchService:
    """Upload tài liệu + tìm kiếm ngữ nghĩa (có bộ lọc) + metadata management."""

    def __init__(self):
        self._loader = DocumentLoader()
        self._retriever = Retriever(k=5, score_threshold=0.3)

    # ── Compatibility methods (No-ops or empty since we migrated to SQLAlchemy) ──
    def _init_db(self):
        pass

    def _migrate_db(self, conn):
        pass

    # ── Database actions using SQLAlchemy ────────────────────────────

    def _save_metadata(
        self,
        file_name: str,
        file_path: str,
        num_chunks: int,
        source_type: str = SOURCE_MANUAL,
        drive_file_id: Optional[str] = None,
        drive_modified_time: Optional[str] = None,
        drive_mime_type: Optional[str] = None,
        user_id: Optional[str] = None,
        file_size: int = 0,
        topic: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> str:
        db = SessionLocal()
        try:
            # Check if doc metadata already exists (e.g. for re-sync/overwrite)
            doc = None
            if drive_file_id:
                doc = db.query(Document).filter(
                    Document.drive_file_id == drive_file_id,
                    Document.user_id == user_id,
                    Document.source_type == source_type
                ).first()
            
            if not doc:
                doc = Document(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    filename=file_name,
                    file_type=file_name.split(".")[-1] if "." in file_name else "txt",
                    file_size=file_size,
                    created_at=datetime.utcnow()
                )
                db.add(doc)
            
            doc.chunk_count = num_chunks
            doc.status = "ready"
            doc.source_type = source_type
            doc.drive_file_id = drive_file_id
            doc.drive_modified_time = drive_modified_time
            doc.drive_mime_type = drive_mime_type
            if topic:
                doc.topic = topic
            if category:
                doc.category = category
            if tags:
                doc.tags = tags
                
            db.commit()
            db.refresh(doc)
            return doc.id
        except Exception as e:
            logger.error(f"DocSearchService._save_metadata error: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    def _delete_metadata_by_drive_id(
        self,
        drive_file_id: str,
        user_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ):
        """Xóa record metadata theo drive_file_id (dùng khi re-sync)."""
        db = SessionLocal()
        try:
            query = db.query(Document).filter(Document.drive_file_id == drive_file_id)
            if user_id:
                query = query.filter(Document.user_id == user_id)
            if source_type:
                query = query.filter(Document.source_type == source_type)
            doc = query.first()
            if doc:
                db.delete(doc)
                db.commit()
        except Exception as e:
            logger.error(f"DocSearchService._delete_metadata_by_drive_id error: {e}")
            db.rollback()
        finally:
            db.close()

    def list_documents(self, user_id: Optional[str] = None) -> List[Dict]:
        """Trả về danh sách tài liệu đã upload (cả manual và Drive/OneDrive)."""
        db = SessionLocal()
        try:
            query = db.query(Document)
            if user_id:
                query = query.filter(Document.user_id == user_id)
            rows = query.order_by(Document.created_at.desc()).all()
            return [
                {
                    "file_name": r.filename,
                    "num_chunks": r.chunk_count,
                    "uploaded_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                    "source_type": r.source_type or SOURCE_MANUAL,
                    "drive_file_id": r.drive_file_id,
                    "drive_modified_time": r.drive_modified_time,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"DocSearchService.list_documents error: {e}")
            return []
        finally:
            db.close()

    def get_drive_document(
        self,
        drive_file_id: str,
        user_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> Optional[Dict]:
        """Lấy metadata của document theo drive_file_id."""
        db = SessionLocal()
        try:
            query = db.query(Document).filter(Document.drive_file_id == drive_file_id)
            if user_id:
                query = query.filter(Document.user_id == user_id)
            if source_type:
                query = query.filter(Document.source_type == source_type)
            r = query.first()
            if not r:
                return None
            return {
                "file_name": r.filename,
                "num_chunks": r.chunk_count,
                "uploaded_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                "drive_modified_time": r.drive_modified_time,
            }
        except Exception as e:
            logger.error(f"DocSearchService.get_drive_document error: {e}")
            return None
        finally:
            db.close()

    # ── Core operations: Manual Upload ─────────────────────────────

    def upload(self, file_path: str, user_id: Optional[str] = None) -> str:
        """Load file → embed → lưu vào ChromaDB + SQLite."""
        path = Path(file_path)
        logger.info(f"DocSearchService.upload: {path.name}")

        chunks = self._loader.load(file_path)
        if not chunks:
            return f"Không thể đọc nội dung từ file {path.name}."

        # Trích xuất văn bản mẫu để phân loại
        text_sample = ""
        if chunks:
            text_sample = "\n".join([c.page_content for c in chunks[:2]])
        
        classification = TopicClassifier.classify(text_sample)
        topic = classification["topic"]
        category = classification["category"]
        tags_list = classification["tags"]
        tags_str = json.dumps(tags_list, ensure_ascii=False)

        # Cập nhật metadata cho ChromaDB
        for chunk in chunks:
            chunk_metadata = {
                "source": path.name,
                "source_type": SOURCE_MANUAL,
                "topic": topic,
                "category": category,
                "tags": tags_str,
            }
            if user_id:
                chunk_metadata["user_id"] = user_id
            chunk.metadata.update(chunk_metadata)

        store = get_vector_store()
        num_added = store.add_documents(chunks)
        
        self._save_metadata(
            file_name=path.name,
            file_path=str(path),
            num_chunks=num_added,
            source_type=SOURCE_MANUAL,
            user_id=user_id,
            file_size=path.stat().st_size if path.exists() else 0,
            topic=topic,
            category=category,
            tags=tags_str,
        )

        return (
            f"✅ Đã nạp tài liệu '{path.name}' thành công!\n"
            f"   📄 {num_added} chunks đã được lưu vào cơ sở dữ liệu tìm kiếm."
        )

    # ── Core operations: Google Drive Import ───────────────────────

    def import_from_drive(
        self,
        file_ids: List[str],
        access_token: str,
        refresh_token: str = "",
        user_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Import danh sách file từ Google Drive vào RAG.
        """
        from services.google_drive_service import GoogleDriveService

        drive_svc = GoogleDriveService(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        results = []
        store = get_vector_store()

        for file_id in file_ids:
            result = {"file_id": file_id, "file_name": "", "status": "error", "num_chunks": 0, "error": None}
            try:
                # Lấy metadata
                meta = drive_svc.get_file_metadata(file_id)
                file_name = meta.get("name", file_id)
                mime_type = meta.get("mimeType", "")
                modified_time = meta.get("modifiedTime", "")
                file_size = int(meta.get("size", 0) or 0)
                result["file_name"] = file_name

                logger.info(f"DocSearchService.import_from_drive: processing '{file_name}' ({mime_type})")

                # Lấy nội dung
                from services.google_drive_service import DriveFile
                drive_file = DriveFile(
                    id=file_id,
                    name=file_name,
                    mime_type=mime_type,
                    modified_time=modified_time,
                )
                ext, content_bytes = drive_svc.get_file_content(drive_file)

                # Cập nhật size nếu export Google Docs
                if not file_size and content_bytes:
                    file_size = len(content_bytes)

                # Build temp metadata cho chunk loader
                temp_metadata = {
                    "source": file_name,
                    "source_type": SOURCE_DRIVE,
                    "drive_file_id": file_id,
                    "drive_modified_time": modified_time,
                    "drive_mime_type": mime_type,
                }
                if user_id:
                    temp_metadata["user_id"] = user_id

                # Chunk theo loại file
                if ext in (".txt", ".csv"):
                    text = content_bytes.decode("utf-8", errors="ignore")
                    chunks = self._loader.load_from_text(text, temp_metadata)
                else:
                    chunks = self._loader.load_from_bytes(content_bytes, ext, temp_metadata)

                if not chunks:
                    result["error"] = "Không trích xuất được nội dung"
                    results.append(result)
                    continue

                # Phân loại chủ đề bằng Gemini
                text_sample = "\n".join([c.page_content for c in chunks[:2]])
                classification = TopicClassifier.classify(text_sample)
                topic = classification["topic"]
                category = classification["category"]
                tags_list = classification["tags"]
                tags_str = json.dumps(tags_list, ensure_ascii=False)

                # Thêm topic/category/tags vào chunk metadata thực tế cho ChromaDB
                for chunk in chunks:
                    chunk.metadata.update({
                        "topic": topic,
                        "category": category,
                        "tags": tags_str
                    })

                # Xóa chunks cũ nếu đã import trước đó (re-import)
                delete_filter = {"$and": [{"drive_file_id": file_id}, {"source_type": SOURCE_DRIVE}]}
                if user_id:
                    delete_filter = {"$and": [{"drive_file_id": file_id}, {"source_type": SOURCE_DRIVE}, {"user_id": user_id}]}
                store.delete_by_metadata(delete_filter)
                self._delete_metadata_by_drive_id(file_id, user_id=user_id, source_type=SOURCE_DRIVE)

                # Lưu vào ChromaDB
                store.add_documents(chunks)
                num_chunks = len(chunks)

                # Lưu metadata SQLite trong orca.db
                self._save_metadata(
                    file_name=file_name,
                    file_path=f"google_drive:{file_id}",
                    num_chunks=num_chunks,
                    source_type=SOURCE_DRIVE,
                    drive_file_id=file_id,
                    drive_modified_time=modified_time,
                    drive_mime_type=mime_type,
                    user_id=user_id,
                    file_size=file_size,
                    topic=topic,
                    category=category,
                    tags=tags_str,
                )

                result.update({"status": "success", "num_chunks": num_chunks})
                logger.info(f"DocSearchService.import_from_drive: '{file_name}' → {num_chunks} chunks ✅")

            except Exception as e:
                result["error"] = str(e)
                logger.error(f"DocSearchService.import_from_drive: lỗi file {file_id}: {e}")

            results.append(result)

        return results

    def sync_drive_document(
        self,
        file_id: str,
        access_token: str,
        refresh_token: str = "",
        user_id: Optional[str] = None,
    ) -> Dict:
        """
        Re-sync một file Drive đã import (kiểm tra modifiedTime trước).
        """
        from services.google_drive_service import GoogleDriveService

        drive_svc = GoogleDriveService(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        try:
            meta = drive_svc.get_file_metadata(file_id)
            current_modified = meta.get("modifiedTime", "")

            # So sánh với version đã lưu
            existing = self.get_drive_document(file_id, user_id=user_id, source_type=SOURCE_DRIVE)
            if existing and existing.get("drive_modified_time") == current_modified:
                return {
                    "status": "skipped",
                    "num_chunks": existing["num_chunks"],
                    "message": f"File '{existing['file_name']}' chưa thay đổi, không cần sync lại.",
                }

            # Re-import
            results = self.import_from_drive([file_id], access_token, refresh_token, user_id=user_id)
            r = results[0]
            if r["status"] == "success":
                return {
                    "status": "updated",
                    "num_chunks": r["num_chunks"],
                    "message": f"✅ Đã cập nhật '{r['file_name']}' với {r['num_chunks']} chunks.",
                }
            else:
                return {"status": "error", "num_chunks": 0, "message": r.get("error", "Lỗi không xác định")}

        except Exception as e:
            logger.error(f"DocSearchService.sync_drive_document: {e}")
            return {"status": "error", "num_chunks": 0, "message": str(e)}

    # ── Core operations: OneDrive Import ───────────────────────────

    def import_from_onedrive(
        self,
        file_ids: List[str],
        access_token: str,
        user_id: Optional[str] = None,
    ) -> List[Dict]:
        """Import selected OneDrive files into RAG."""
        from services.onedrive_service import OneDriveFile, OneDriveService

        drive_svc = OneDriveService(access_token=access_token)
        results = []
        store = get_vector_store()

        for file_id in file_ids:
            result = {"file_id": file_id, "file_name": "", "status": "error", "num_chunks": 0, "error": None}
            try:
                meta = drive_svc.get_file_metadata(file_id)
                file_name = meta.get("name", file_id)
                mime_type = meta.get("mimeType", "")
                modified_time = meta.get("modifiedTime", "")
                file_size = int(meta.get("size", 0) or 0)
                result["file_name"] = file_name

                logger.info(f"DocSearchService.import_from_onedrive: processing '{file_name}' ({mime_type})")

                drive_file = OneDriveFile(
                    id=file_id,
                    name=file_name,
                    mime_type=mime_type,
                    modified_time=modified_time,
                    size=file_size,
                )
                ext, content_bytes = drive_svc.get_file_content(drive_file)

                # Temp metadata for chunk loader
                temp_metadata = {
                    "source": file_name,
                    "source_type": SOURCE_ONEDRIVE,
                    "drive_file_id": file_id,
                    "drive_modified_time": modified_time,
                    "drive_mime_type": mime_type,
                }
                if user_id:
                    temp_metadata["user_id"] = user_id

                if ext in (".txt", ".csv"):
                    text = content_bytes.decode("utf-8", errors="ignore")
                    chunks = self._loader.load_from_text(text, temp_metadata)
                else:
                    chunks = self._loader.load_from_bytes(content_bytes, ext, temp_metadata)

                if not chunks:
                    result["error"] = "Không trích xuất được nội dung"
                    results.append(result)
                    continue

                # Phân loại chủ đề bằng Gemini
                text_sample = "\n".join([c.page_content for c in chunks[:2]])
                classification = TopicClassifier.classify(text_sample)
                topic = classification["topic"]
                category = classification["category"]
                tags_list = classification["tags"]
                tags_str = json.dumps(tags_list, ensure_ascii=False)

                # Thêm topic/category/tags vào chunk metadata thực tế cho ChromaDB
                for chunk in chunks:
                    chunk.metadata.update({
                        "topic": topic,
                        "category": category,
                        "tags": tags_str
                    })

                delete_filter = {"$and": [{"drive_file_id": file_id}, {"source_type": SOURCE_ONEDRIVE}]}
                if user_id:
                    delete_filter = {"$and": [{"drive_file_id": file_id}, {"source_type": SOURCE_ONEDRIVE}, {"user_id": user_id}]}
                store.delete_by_metadata(delete_filter)
                self._delete_metadata_by_drive_id(file_id, user_id=user_id, source_type=SOURCE_ONEDRIVE)

                store.add_documents(chunks)
                num_chunks = len(chunks)

                self._save_metadata(
                    file_name=file_name,
                    file_path=f"onedrive:{file_id}",
                    num_chunks=num_chunks,
                    source_type=SOURCE_ONEDRIVE,
                    drive_file_id=file_id,
                    drive_modified_time=modified_time,
                    drive_mime_type=mime_type,
                    user_id=user_id,
                    file_size=file_size,
                    topic=topic,
                    category=category,
                    tags=tags_str,
                )

                result.update({"status": "success", "num_chunks": num_chunks})
                logger.info(f"DocSearchService.import_from_onedrive: '{file_name}' -> {num_chunks} chunks ✅")

            except Exception as e:
                result["error"] = str(e)
                logger.error(f"DocSearchService.import_from_onedrive: error file {file_id}: {e}")

            results.append(result)

        return results

    def sync_onedrive_document(
        self,
        file_id: str,
        access_token: str,
        user_id: Optional[str] = None,
    ) -> Dict:
        """Re-sync a OneDrive file if its modified time changed."""
        from services.onedrive_service import OneDriveService

        drive_svc = OneDriveService(access_token=access_token)

        try:
            meta = drive_svc.get_file_metadata(file_id)
            current_modified = meta.get("modifiedTime", "")

            existing = self.get_drive_document(file_id, user_id=user_id, source_type=SOURCE_ONEDRIVE)
            if existing and existing.get("drive_modified_time") == current_modified:
                return {
                    "status": "skipped",
                    "num_chunks": existing["num_chunks"],
                    "message": f"File '{existing['file_name']}' chưa thay đổi, không cần sync lại.",
                }

            results = self.import_from_onedrive([file_id], access_token, user_id=user_id)
            r = results[0]
            if r["status"] == "success":
                return {
                    "status": "updated",
                    "num_chunks": r["num_chunks"],
                    "message": f"Đã cập nhật '{r['file_name']}' với {r['num_chunks']} chunks.",
                }
            return {"status": "error", "num_chunks": 0, "message": r.get("error", "Lỗi không xác định")}

        except Exception as e:
            logger.error(f"DocSearchService.sync_onedrive_document: {e}")
            return {"status": "error", "num_chunks": 0, "message": str(e)}

    def search(self, query: str, document_name: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Tìm kiếm tài liệu liên quan và trả về context."""
        docs = self._retriever.retrieve(query, document_name=document_name, user_id=user_id)
        return self._retriever.format_context(docs)


# Singleton
_service: DocSearchService | None = None

def get_doc_search_service() -> DocSearchService:
    global _service
    if _service is None:
        _service = DocSearchService()
    return _service
