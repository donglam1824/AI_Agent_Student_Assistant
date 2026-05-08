"""
services/doc_search_service.py
-------------------------------
DocSearchService: orchestrate upload và search,
quản lý metadata tài liệu trong SQLite.

Hỗ trợ 2 nguồn tài liệu:
  1. Manual upload (PDF, DOCX, TXT từ giao diện web)
  2. Google Drive (import file đã chọn hoặc sync lại)
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from rag.document_loader import DocumentLoader
from rag.vector_store import get_vector_store
from rag.retriever import Retriever
from core.logger import logger

DB_PATH = Path(__file__).parent.parent / "data" / "documents.db"

# Source type constants
SOURCE_MANUAL = "manual_upload"
SOURCE_DRIVE = "google_drive"


class DocSearchService:
    """Upload tài liệu + tìm kiếm ngữ nghĩa (có bộ lọc) + metadata management."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._loader = DocumentLoader()
        self._retriever = Retriever(k=5, score_threshold=0.3)

    # ── SQLite metadata ────────────────────────────────────────────

    def _init_db(self):
        """Tạo bảng documents nếu chưa có (schema mở rộng hỗ trợ Drive)."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    num_chunks INTEGER DEFAULT 0,
                    uploaded_at TEXT NOT NULL,
                    source_type TEXT DEFAULT 'manual_upload',
                    drive_file_id TEXT,
                    drive_modified_time TEXT,
                    drive_mime_type TEXT
                )
            """)
            # Migration: thêm cột mới nếu chưa có (cho DB cũ)
            self._migrate_db(conn)

    def _migrate_db(self, conn):
        """Thêm cột mới vào bảng cũ nếu chưa có (safe migration)."""
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        migrations = [
            ("source_type",        "TEXT DEFAULT 'manual_upload'"),
            ("drive_file_id",      "TEXT"),
            ("drive_modified_time","TEXT"),
            ("drive_mime_type",    "TEXT"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing_columns:
                conn.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_def}")
                logger.info(f"DocSearchService: migrated column '{col_name}'")

    def _save_metadata(
        self,
        file_name: str,
        file_path: str,
        num_chunks: int,
        source_type: str = SOURCE_MANUAL,
        drive_file_id: Optional[str] = None,
        drive_modified_time: Optional[str] = None,
        drive_mime_type: Optional[str] = None,
    ):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO documents
                   (file_name, file_path, num_chunks, uploaded_at,
                    source_type, drive_file_id, drive_modified_time, drive_mime_type)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    file_name, file_path, num_chunks,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    source_type, drive_file_id, drive_modified_time, drive_mime_type,
                ),
            )

    def _delete_metadata_by_drive_id(self, drive_file_id: str):
        """Xóa record metadata theo drive_file_id (dùng khi re-sync)."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM documents WHERE drive_file_id=?", (drive_file_id,))

    def list_documents(self) -> List[Dict]:
        """Trả về danh sách tài liệu đã upload (cả manual và Drive)."""
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """SELECT file_name, num_chunks, uploaded_at,
                          source_type, drive_file_id, drive_modified_time
                   FROM documents ORDER BY id DESC"""
            ).fetchall()
        return [
            {
                "file_name": r[0],
                "num_chunks": r[1],
                "uploaded_at": r[2],
                "source_type": r[3] or SOURCE_MANUAL,
                "drive_file_id": r[4],
                "drive_modified_time": r[5],
            }
            for r in rows
        ]

    def get_drive_document(self, drive_file_id: str) -> Optional[Dict]:
        """Lấy metadata của document theo drive_file_id."""
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT file_name, num_chunks, uploaded_at, drive_modified_time FROM documents WHERE drive_file_id=?",
                (drive_file_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "file_name": row[0],
            "num_chunks": row[1],
            "uploaded_at": row[2],
            "drive_modified_time": row[3],
        }

    # ── Core operations: Manual Upload ─────────────────────────────

    def upload(self, file_path: str) -> str:
        """Load file → embed → lưu vào ChromaDB + SQLite."""
        path = Path(file_path)
        logger.info(f"DocSearchService.upload: {path.name}")

        chunks = self._loader.load(file_path)
        if not chunks:
            return f"Không thể đọc nội dung từ file {path.name}."

        store = get_vector_store()
        num_added = store.add_documents(chunks)
        self._save_metadata(path.name, str(path), num_added, source_type=SOURCE_MANUAL)

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
    ) -> List[Dict]:
        """
        Import danh sách file từ Google Drive vào RAG.

        Args:
            file_ids: Danh sách Google Drive file ID cần import.
            access_token: Google OAuth2 access token của user.
            refresh_token: Refresh token (tùy chọn).
        Returns:
            Danh sách kết quả: [{file_id, file_name, status, num_chunks, error}]
        """
        from services.google_drive_service import GoogleDriveService, GOOGLE_EXPORT_MAP

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

                # Build metadata cho ChromaDB
                chunk_metadata = {
                    "source": file_name,
                    "source_type": SOURCE_DRIVE,
                    "drive_file_id": file_id,
                    "drive_modified_time": modified_time,
                    "drive_mime_type": mime_type,
                }

                # Chunk theo loại file
                if ext in (".txt", ".csv"):
                    text = content_bytes.decode("utf-8", errors="ignore")
                    chunks = self._loader.load_from_text(text, chunk_metadata)
                else:
                    chunks = self._loader.load_from_bytes(content_bytes, ext, chunk_metadata)

                if not chunks:
                    result["error"] = "Không trích xuất được nội dung"
                    results.append(result)
                    continue

                # Xóa chunks cũ nếu đã import trước đó (re-import)
                self._delete_metadata_by_drive_id(file_id)

                # Lưu vào ChromaDB
                store.add_documents(chunks)
                num_chunks = len(chunks)

                # Lưu metadata SQLite
                self._save_metadata(
                    file_name=file_name,
                    file_path=f"google_drive:{file_id}",
                    num_chunks=num_chunks,
                    source_type=SOURCE_DRIVE,
                    drive_file_id=file_id,
                    drive_modified_time=modified_time,
                    drive_mime_type=mime_type,
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
    ) -> Dict:
        """
        Re-sync một file Drive đã import (kiểm tra modifiedTime trước).

        Returns:
            {"status": "updated"|"skipped"|"error", "num_chunks": int, "message": str}
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
            existing = self.get_drive_document(file_id)
            if existing and existing.get("drive_modified_time") == current_modified:
                return {
                    "status": "skipped",
                    "num_chunks": existing["num_chunks"],
                    "message": f"File '{existing['file_name']}' chưa thay đổi, không cần sync lại.",
                }

            # Re-import
            results = self.import_from_drive([file_id], access_token, refresh_token)
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

    # ── Search ─────────────────────────────────────────────────────

    def search(self, query: str, document_name: Optional[str] = None) -> str:
        """Tìm kiếm tài liệu liên quan và trả về context."""
        docs = self._retriever.retrieve(query, document_name=document_name)
        return self._retriever.format_context(docs)


# Singleton
_service: DocSearchService | None = None

def get_doc_search_service() -> DocSearchService:
    global _service
    if _service is None:
        _service = DocSearchService()
    return _service
