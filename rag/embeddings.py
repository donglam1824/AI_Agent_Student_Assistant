"""
rag/embeddings.py
-----------------
Google Gemini Embedding wrapper – nhất quán với LLM backend hiện tại.
Model: models/embedding-001
"""
from functools import lru_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config.settings import settings
from core.logger import logger


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Singleton: trả về embedding model (lazy init + cache)."""
    logger.info("Embeddings: khởi tạo GoogleGenerativeAIEmbeddings")
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=settings.gemini_api_key,
    )
