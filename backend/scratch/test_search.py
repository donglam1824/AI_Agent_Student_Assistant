import os
# Force offline mode for Hugging Face to avoid hanging on internet checks
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.vector_store import get_vector_store
from rag.retriever import Retriever
from core.logger import logger

logger.remove()

def main():
    store = get_vector_store()
    print(f"ChromaDB Collection Count: {store.count()}")
    
    # Try a few queries based on common student questions
    queries = [
        "cơ sở dữ liệu",
        "định nghĩa",
        "chương 1",
        "khái niệm",
        "C1"
    ]
    
    for query in queries:
        print(f"\n========================================")
        print(f"Query: '{query}'")
        print(f"========================================")
        results = store.similarity_search_with_score(query, k=5)
        print("Raw similarity search scores (relevance scores):")
        for i, (doc, score) in enumerate(results):
            print(f"[{i}] Score: {score:.4f}")
            print(f"    Source: {doc.metadata.get('source')} | User: {doc.metadata.get('user_id')}")
            print(f"    Content preview: {repr(doc.page_content[:150])}")
        
        # Test with Retriever threshold 0.3
        retriever_30 = Retriever(k=5, score_threshold=0.3)
        docs_30 = retriever_30.retrieve(query)
        print(f"\nRetriever (threshold 0.3) found: {len(docs_30)} docs")
        
        # Test with Retriever threshold 0.5
        retriever_50 = Retriever(k=5, score_threshold=0.5)
        docs_50 = retriever_50.retrieve(query)
        print(f"Retriever (threshold 0.5) found: {len(docs_50)} docs")

if __name__ == "__main__":
    main()
