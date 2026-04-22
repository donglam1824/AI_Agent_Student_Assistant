"""
tools/doc_search/list_documents.py
------------------------------------
LangChain tool: liệt kê các tài liệu đã upload.
"""
from langchain_core.tools import tool
from services.doc_search_service import get_doc_search_service
from core.logger import logger


@tool
def list_documents() -> str:
    """
    Liệt kê tất cả tài liệu đã được upload vào hệ thống tìm kiếm.
    Cung cấp danh sách tên tài liệu (document_name) để có thể dùng cho metadata filter.
    """
    service = get_doc_search_service()
    try:
        docs = service.list_documents()
        if not docs:
            return "📚 Chưa có tài liệu nào được upload. Hãy dùng lệnh upload để thêm tài liệu."
        
        lines = ["📚 Danh sách tài liệu đã lưu:\n"]
        for i, doc in enumerate(docs, 1):
            lines.append(
                f"  {i}. {doc['file_name']} "
                f"– {doc['num_chunks']} chunks "
                f"– Upload: {doc['uploaded_at']}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_documents error: {e}")
        return f"❌ Lỗi khi lấy danh sách: {e}"
