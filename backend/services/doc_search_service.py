"""
services/doc_search_service.py
-------------------------------
DocSearchService: orchestrate upload và search,
quản lý metadata tài liệu trong SQLite.
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


class DocSearchService:
    """Upload tài liệu + tìm kiếm ngữ nghĩa (có bộ lọc) + metadata management."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._loader = DocumentLoader()
        self._retriever = Retriever(k=5, score_threshold=0.3)

    # ── SQLite metadata ────────────────────────────────────────────

    def _init_db(self):
        """Tạo bảng documents nếu chưa có."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    num_chunks INTEGER DEFAULT 0,
                    uploaded_at TEXT NOT NULL
                )
            """)

    def _save_metadata(self, file_name: str, file_path: str, num_chunks: int):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO documents (file_name, file_path, num_chunks, uploaded_at) VALUES (?,?,?,?)",
                (file_name, file_path, num_chunks, datetime.now().strftime("%Y-%m-%d %H:%M")),
            )

    def list_documents(self) -> List[Dict]:
        """Trả về danh sách tài liệu đã upload."""
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT file_name, num_chunks, uploaded_at FROM documents ORDER BY id DESC"
            ).fetchall()
        return [
            {"file_name": r[0], "num_chunks": r[1], "uploaded_at": r[2]}
            for r in rows
        ]

    # ── Core operations ────────────────────────────────────────────

    def upload(self, file_path: str) -> str:
        """Load file → embed → lưu vào ChromaDB + SQLite."""
        path = Path(file_path)
        logger.info(f"DocSearchService.upload: {path.name}")

        chunks = self._loader.load(file_path)
        if not chunks:
            return f"Không thể đọc nội dung từ file {path.name}."

        store = get_vector_store()
        num_added = store.add_documents(chunks)
        self._save_metadata(path.name, str(path), num_added)

        return (
            f"✅ Đã nạp tài liệu '{path.name}' thành công!\n"
            f"   📄 {num_added} chunks đã được lưu vào cơ sở dữ liệu tìm kiếm."
        )

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
