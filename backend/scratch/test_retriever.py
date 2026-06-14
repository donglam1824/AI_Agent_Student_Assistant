import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.vector_store import get_vector_store
from services.doc_search_service import get_doc_search_service
from db.database import SessionLocal
from db.models import Document
from core.logger import logger

logger.remove()  # clean output

def main():
    db = SessionLocal()
    try:
        sqlite_docs = db.query(Document).all()
        print(f"--- SQLite Documents Count: {len(sqlite_docs)} ---")
        for doc in sqlite_docs:
            print(f"ID: {doc.id} | Name: {doc.filename} | User: {doc.user_id} | Chunks: {doc.chunk_count} | Status: {doc.status}")
    finally:
        db.close()

    store = get_vector_store()
    print(f"\n--- ChromaDB Collection Count: {store.count()} ---")

    # Let's perform a sample search
    query = "định nghĩa"
    print(f"\nSearching for: '{query}'")
    results = store.similarity_search_with_score(query, k=5)
    print(f"Results from store.similarity_search_with_score (similarity_search_with_relevance_scores):")
    for i, (doc, score) in enumerate(results):
        print(f"[{i}] Score: {score}")
        print(f"    Source: {doc.metadata.get('source')} | User: {doc.metadata.get('user_id')}")
        print(f"    Content preview: {doc.page_content[:150]}...")

    # Let's search with retriever
    from rag.retriever import Retriever
    retriever = Retriever(k=5, score_threshold=0.3)
    docs = retriever.retrieve(query)
    print(f"\nRetriever (threshold 0.3) found {len(docs)} documents.")

    retriever_high = Retriever(k=5, score_threshold=0.5)
    docs_high = retriever_high.retrieve(query)
    print(f"Retriever (threshold 0.5) found {len(docs_high)} documents.")

if __name__ == "__main__":
    main()
