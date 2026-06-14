"""
rag/enrichment.py
-----------------
Helpers for enriching chunks before vector indexing.
"""
from __future__ import annotations

from typing import Iterable

from langchain_core.documents import Document


RAW_CONTENT_METADATA_LIMIT = 12000


def prepare_chunks_for_index(chunks: Iterable[Document]) -> None:
    """
    Embed contextual text while preserving the original chunk for answer context.

    Existing retrieval already stores source/topic/wiki summary in metadata. Chroma
    embeds only page_content, so new chunks should include that context in the text
    being embedded. The original content remains in metadata["raw_content"] so the
    response formatter can avoid duplicate prefixes.
    """
    for chunk in chunks:
        if chunk.metadata.get("retrieval_enriched") is True:
            continue

        context_prefix = str(chunk.metadata.get("context_prefix") or "").strip()
        if not context_prefix:
            continue

        original = chunk.page_content or ""
        chunk.metadata["raw_content"] = original[:RAW_CONTENT_METADATA_LIMIT]
        chunk.metadata["retrieval_enriched"] = True
        chunk.page_content = f"{context_prefix}\n\n--- Noi dung doan ---\n{original}"
