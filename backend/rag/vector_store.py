"""
rag/vector_store.py
-------------------
ChromaDB vector store operations.
Lưu dữ liệu tại: data/chroma_db/ (persistent local)
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import warnings

from langchain_chroma import Chroma
from langchain_core.documents import Document

from rag.embeddings import get_embedding_collection_name, get_embeddings
from core.logger import logger

# Đường dẫn lưu ChromaDB
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"


def _open_collection_without_embeddings() -> Chroma:
    """Open the current Chroma collection without loading the embedding model."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    collection_name = get_embedding_collection_name()
    return Chroma(
        collection_name=collection_name,
        persist_directory=str(CHROMA_DIR),
    )


class VectorStore:
    """Quản lý ChromaDB collection cho tài liệu sinh viên."""

    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        collection_name = get_embedding_collection_name()
        self._db = Chroma(
            collection_name=collection_name,
            embedding_function=get_embeddings(),
            persist_directory=str(CHROMA_DIR),
        )
        logger.info(f"VectorStore: collection={collection_name}, dir={CHROMA_DIR}")

    def add_documents(self, documents: List[Document]) -> int:
        """Thêm chunks vào ChromaDB. Trả về số chunks đã thêm."""
        if not documents:
            return 0
        self._db.add_documents(documents)
        logger.info(f"VectorStore: đã thêm {len(documents)} chunks")
        return len(documents)

    def delete_by_metadata(self, where: Dict[str, Any]) -> None:
        """Delete chunks matching a Chroma metadata filter."""
        if not where:
            return
        self._db._collection.delete(where=where)
        logger.info(f"VectorStore: deleted chunks where={where}")

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Tìm k chunks có độ liên quan nhất với query (kèm theo điểm relevance score).
        Hỗ trợ filter theo metadata (vd filter = {"source": "file_name"}).
        Lưu ý: score mà ChromaDB trả về là distance (càng nhỏ càng giống).
        Do Langchain đã map thành relevance_score (càng gần 1 càng giống).
        """
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Relevance scores must be between 0 and 1.*",
                category=UserWarning,
            )
            results = self._db.similarity_search_with_relevance_scores(
                query=query, k=k, filter=filter
            )
        logger.debug(f"VectorStore: tìm '{query[:50]}...' → {len(results)} kết quả")
        return results

    def get_documents(
        self,
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 1000,
    ) -> List[Document]:
        """Return stored chunks for local lexical reranking/fallback."""
        kwargs: Dict[str, Any] = {
            "include": ["documents", "metadatas"],
            "limit": limit,
        }
        if filter:
            kwargs["where"] = filter

        result = self._db._collection.get(**kwargs)
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        docs: List[Document] = []
        for i, content in enumerate(documents):
            metadata = dict(metadatas[i] or {}) if i < len(metadatas) else {}
            if i < len(ids):
                metadata["_chroma_id"] = ids[i]
            docs.append(Document(page_content=content or "", metadata=metadata))
        return docs

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


def delete_vectors_by_metadata(where: Dict[str, Any]) -> None:
    """Delete chunks without initializing local/API embedding providers."""
    if not where:
        return
    db = _open_collection_without_embeddings()
    db._collection.delete(where=where)
    logger.info(f"VectorStore: deleted chunks where={where}")
