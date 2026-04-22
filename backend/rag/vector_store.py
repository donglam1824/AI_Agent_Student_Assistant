"""
rag/vector_store.py
-------------------
ChromaDB vector store operations.
Lưu dữ liệu tại: data/chroma_db/ (persistent local)
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from rag.embeddings import get_embeddings
from core.logger import logger

# Đường dẫn lưu ChromaDB
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION_NAME = "student_documents"


class VectorStore:
    """Quản lý ChromaDB collection cho tài liệu sinh viên."""

    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._db = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=str(CHROMA_DIR),
        )
        logger.info(f"VectorStore: collection={COLLECTION_NAME}, dir={CHROMA_DIR}")

    def add_documents(self, documents: List[Document]) -> int:
        """Thêm chunks vào ChromaDB. Trả về số chunks đã thêm."""
        if not documents:
            return 0
        self._db.add_documents(documents)
        logger.info(f"VectorStore: đã thêm {len(documents)} chunks")
        return len(documents)

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Tìm k chunks có độ liên quan nhất với query (kèm theo điểm relevance score).
        Hỗ trợ filter theo metadata (vd filter = {"source": "file_name"}).
        Lưu ý: score mà ChromaDB trả về là distance (càng nhỏ càng giống).
        Do Langchain đã map thành relevance_score (càng gần 1 càng giống).
        """
        results = self._db.similarity_search_with_relevance_scores(
            query=query, k=k, filter=filter
        )
        logger.debug(f"VectorStore: tìm '{query[:50]}...' → {len(results)} kết quả")
        return results

    def count(self) -> int:
        """Số chunks hiện có trong collection."""
        return self._db._collection.count()


# Singleton
_vector_store: VectorStore | None = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
