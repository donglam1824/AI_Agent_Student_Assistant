"""
rag/retriever.py
----------------
High-level retriever: tìm kiếm + format context để đưa vào LLM.
Áp dụng score threshold để loại bỏ các kết quả không liên quan.
"""
from typing import List, Optional
from langchain_core.documents import Document
from rag.vector_store import get_vector_store
from core.logger import logger


class Retriever:
    """Semantic search + format kết quả + filter."""

    def __init__(self, k: int = 5, score_threshold: float = 0.5):
        self._k = k
        self._score_threshold = score_threshold

    def retrieve(self, query: str, document_name: Optional[str] = None) -> List[Document]:
        """Trả về top-k chunks liên quan nhất, lọc theo score threshold và metadata (tùy chọn)."""
        store = get_vector_store()
        if store.count() == 0:
            logger.warning("Retriever: ChromaDB trống, chưa có tài liệu nào.")
            return []

        # Xây dựng filter theo document_name nếu có
        filter_dict = None
        if document_name:
            filter_dict = {"source": document_name}
        
        results_with_score = store.similarity_search_with_score(
            query=query, k=self._k, filter=filter_dict
        )

        valid_docs = []
        for doc, score in results_with_score:
            logger.debug(f"Retriever: doc_source={doc.metadata.get('source')} score={score}")
            if score >= self._score_threshold:
                valid_docs.append(doc)

        if not valid_docs:
            logger.info(f"Retriever: Không tìm thấy chunks nào pass threshold {self._score_threshold}")
            
        return valid_docs

    def format_context(self, docs: List[Document]) -> str:
        """Gộp các chunks thành 1 chuỗi context để đưa vào LLM."""
        if not docs:
            return "Không tìm thấy tài liệu nào đáp ứng hoặc đủ độ tương đồng với câu hỏi."
        
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Không rõ nguồn")
            page = doc.metadata.get("page", "")
            page_info = f" (trang {page})" if page else ""
            parts.append(f"[{i}] Từ: {source}{page_info}\n{doc.page_content}")
        
        return "\n\n---\n\n".join(parts)
