"""
rag/retriever.py
----------------
Hybrid retriever for document RAG.

The first pass uses Chroma semantic search. A local lexical pass then searches
the same filtered candidate pool and reranks with keyword, phrase, and metadata
signals. This keeps the default path local while making short or vague
Vietnamese questions less brittle.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from core.logger import logger
from rag.vector_store import get_vector_store


_STOPWORDS = {
    "la", "gi", "giai", "thich", "hay", "cho", "toi", "biet", "ve", "trong",
    "tai", "lieu", "file", "pdf", "doc", "docx", "ppt", "pptx", "noi", "dung", "cua", "mot",
    "cac", "nhung", "nhu", "the", "nao", "vi", "du", "tom", "tat", "can",
    "phan", "tich", "so", "sanh", "neu", "trinh", "bay", "su", "dung",
}


@dataclass
class _Candidate:
    doc: Document
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    final_score: float = 0.0


class Retriever:
    """Semantic search + local lexical rerank + context formatting."""

    def __init__(
        self,
        k: int = 5,
        score_threshold: float = 0.5,
        candidate_k: Optional[int] = None,
        lexical_pool_limit: int = 1000,
    ):
        self._k = k
        self._score_threshold = score_threshold
        self._candidate_k = max(candidate_k or k * 5, k)
        self._lexical_pool_limit = lexical_pool_limit

    def retrieve(
        self,
        query: str,
        document_name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """Return reranked top-k chunks matching semantic and lexical signals."""
        store = get_vector_store()
        if store.count() == 0:
            logger.warning("Retriever: ChromaDB is empty.")
            return []

        filter_dict = self._build_filter(
            document_name=document_name,
            user_id=user_id,
            metadata_filter=metadata_filter,
        )

        query_tokens = self._tokenize(query)
        normalized_query = self._normalize(query)
        candidates: Dict[str, _Candidate] = {}

        semantic_results = store.similarity_search_with_score(
            query=query,
            k=self._candidate_k,
            filter=filter_dict,
        )
        for doc, score in semantic_results:
            key = self._doc_key(doc)
            candidate = candidates.setdefault(key, _Candidate(doc=doc))
            candidate.semantic_score = max(candidate.semantic_score, self._clamp_score(score))

        # Local lexical fallback over the same scoped corpus. This improves
        # queries where embeddings under-score exact Vietnamese terms.
        for doc in store.get_documents(filter=filter_dict, limit=self._lexical_pool_limit):
            lexical_score = self._lexical_score(query_tokens, normalized_query, doc)
            if lexical_score <= 0:
                continue
            key = self._doc_key(doc)
            candidate = candidates.setdefault(key, _Candidate(doc=doc))
            candidate.lexical_score = max(candidate.lexical_score, lexical_score)

        ranked = self._rerank(candidates.values(), normalized_query)
        valid = [
            c.doc
            for c in ranked
            if c.final_score >= self._score_threshold
            or c.semantic_score >= self._score_threshold
            or c.lexical_score >= 0.18
        ]

        if not valid and ranked:
            best = ranked[0]
            if best.semantic_score >= 0.08 or best.lexical_score >= 0.12:
                valid = [best.doc]

        if not valid:
            logger.info(
                "Retriever: no chunks passed hybrid threshold "
                f"threshold={self._score_threshold}, query={query!r}"
            )

        return valid[: self._k]

    def format_context(self, docs: List[Document]) -> str:
        """Join chunks into a context string for the answer LLM."""
        if not docs:
            return "Không tìm thấy tài liệu nào đáp ứng hoặc đủ độ tương đồng với câu hỏi."

        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Không rõ nguồn")
            page = doc.metadata.get("page", "")
            page_info = f" (trang {page})" if page else ""
            content = doc.metadata.get("raw_content") or doc.page_content
            context_prefix = doc.metadata.get("context_prefix", "")
            if context_prefix:
                content = f"{context_prefix}\n\n--- Nội dung đoạn ---\n{content}"
            parts.append(f"[{i}] Từ: {source}{page_info}\n{content}")

        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _build_filter(
        *,
        document_name: Optional[str],
        user_id: Optional[str],
        metadata_filter: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        filters = []
        if metadata_filter:
            filters.append(metadata_filter)
        if document_name:
            filters.append({"source": document_name})
        if user_id:
            filters.append({"user_id": user_id})

        if len(filters) == 1:
            return filters[0]
        if len(filters) > 1:
            return {"$and": filters}
        return None

    def _rerank(self, candidates: Any, normalized_query: str) -> List[_Candidate]:
        ranked: List[_Candidate] = []
        for candidate in candidates:
            metadata_boost = self._metadata_boost(normalized_query, candidate.doc)
            candidate.final_score = (
                0.42 * candidate.semantic_score
                + 0.52 * candidate.lexical_score
                + metadata_boost
            )
            ranked.append(candidate)

        ranked.sort(
            key=lambda c: (
                c.final_score,
                c.semantic_score,
                c.lexical_score,
            ),
            reverse=True,
        )
        for c in ranked[: self._k]:
            logger.debug(
                "Retriever rank: "
                f"source={c.doc.metadata.get('source')} "
                f"page={c.doc.metadata.get('page')} "
                f"semantic={c.semantic_score:.3f} "
                f"lexical={c.lexical_score:.3f} "
                f"final={c.final_score:.3f}"
            )
        return ranked

    def _lexical_score(
        self,
        query_tokens: set[str],
        normalized_query: str,
        doc: Document,
    ) -> float:
        if not query_tokens:
            return 0.0

        text = self._scoring_text(doc)
        normalized_text = self._normalize(text)
        doc_tokens = set(self._tokenize(normalized_text))
        if not doc_tokens:
            return 0.0

        overlap = len(query_tokens.intersection(doc_tokens)) / max(len(query_tokens), 1)
        phrase = 1.0 if len(normalized_query) >= 4 and normalized_query in normalized_text else 0.0
        ordered_hits = sum(1 for token in query_tokens if token in normalized_text)
        coverage = ordered_hits / max(len(query_tokens), 1)
        return min(1.0, 0.55 * overlap + 0.30 * phrase + 0.15 * coverage)

    def _metadata_boost(self, normalized_query: str, doc: Document) -> float:
        metadata_text = " ".join(
            str(doc.metadata.get(key) or "")
            for key in ("source", "topic", "category", "tags", "context_summary")
        )
        normalized_metadata = self._normalize(metadata_text)
        boost = 0.0
        if len(normalized_query) >= 4 and normalized_query in normalized_metadata:
            boost += 0.10
        query_tokens = self._tokenize(normalized_query)
        metadata_tokens = set(self._tokenize(normalized_metadata))
        if query_tokens:
            boost += 0.08 * (
                len(query_tokens.intersection(metadata_tokens)) / max(len(query_tokens), 1)
            )
        return min(boost, 0.16)

    @staticmethod
    def _scoring_text(doc: Document) -> str:
        return "\n".join(
            str(part or "")
            for part in (
                doc.page_content,
                doc.metadata.get("raw_content"),
                doc.metadata.get("context_prefix"),
                doc.metadata.get("context_summary"),
                doc.metadata.get("source"),
                doc.metadata.get("topic"),
                doc.metadata.get("category"),
                doc.metadata.get("tags"),
            )
        )

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        normalized = cls._normalize(text)
        tokens = set(re.findall(r"[a-z0-9_]{2,}", normalized))
        return {token for token in tokens if token not in _STOPWORDS}

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFD", (text or "").lower())
        without_marks = "".join(
            ch for ch in normalized if unicodedata.category(ch) != "Mn"
        )
        return re.sub(r"\s+", " ", without_marks).strip()

    @staticmethod
    def _clamp_score(score: float) -> float:
        try:
            return max(0.0, min(float(score), 1.0))
        except Exception:
            return 0.0

    @staticmethod
    def _doc_key(doc: Document) -> str:
        metadata = doc.metadata or {}
        return str(
            metadata.get("_chroma_id")
            or "|".join(
                str(metadata.get(key) or "")
                for key in ("user_id", "doc_id", "drive_file_id", "source", "page")
            )
            or hash(doc.page_content)
        )
