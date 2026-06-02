"""
rag/embeddings.py
-----------------
Embedding provider router for RAG.

Default is a local sentence-transformers model to avoid API quota during
document ingestion. Gemini/OpenAI remain available through environment config.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import re
from typing import List

from langchain_core.embeddings import Embeddings

from config.settings import settings
from core.logger import logger


class LocalSentenceTransformerEmbeddings(Embeddings):
    """LangChain-compatible wrapper around sentence-transformers."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        logger.info(f"Embeddings: loading local sentence-transformers model={model_name}")
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=settings.embedding_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        vector = self._model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()


def _build_local_embeddings() -> Embeddings:
    return LocalSentenceTransformerEmbeddings(settings.embedding_model)


def _build_gemini_embeddings() -> Embeddings:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    logger.info(f"Embeddings: loading Gemini embedding model={settings.embedding_model}")
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.gemini_api_key,
    )


def _build_openai_embeddings() -> Embeddings:
    from langchain_openai import OpenAIEmbeddings

    logger.info(f"Embeddings: loading OpenAI embedding model={settings.embedding_model}")
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Return the configured embedding function."""
    provider = settings.embedding_provider.lower().strip()
    if provider == "local":
        return _build_local_embeddings()
    if provider == "gemini":
        return _build_gemini_embeddings()
    if provider == "openai":
        return _build_openai_embeddings()
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}. "
        "Use 'local', 'gemini', or 'openai'."
    )


def get_embedding_collection_name() -> str:
    """Stable Chroma collection name scoped to the embedding provider/model."""
    provider = settings.embedding_provider.lower().strip()
    model = settings.embedding_model.strip()
    raw_name = f"student_documents_{provider}_{model}"
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", raw_name).strip("._-")
    digest = hashlib.sha1(raw_name.encode("utf-8")).hexdigest()[:8]
    name = f"{slug[:50]}_{digest}"
    return name if len(name) >= 3 else f"docs_{digest}"
