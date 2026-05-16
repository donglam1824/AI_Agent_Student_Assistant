"""
tools/doc_search/list_documents.py
------------------------------------
LangChain tool: liệt kê các tài liệu đã upload.
"""
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from services.doc_search_service import get_doc_search_service
from core.logger import logger


@tool
def list_documents(config: RunnableConfig = None) -> str:
    """
    Liệt kê tất cả tài liệu đã được upload vào hệ thống tìm kiếm.
    Cung cấp danh sách tên tài liệu (document_name) để có thể dùng cho metadata filter.
    """
    service = get_doc_search_service()
    user_id = (config or {}).get("configurable", {}).get("user_id")
    try:
        docs = service.list_documents(user_id=user_id)
        if not docs:
            return "Chua co tai lieu nao duoc upload. Hay dung lenh upload de them tai lieu."
        
        lines = ["Danh sach tai lieu da luu:\n"]
        for i, doc in enumerate(docs, 1):
            source_icon = "[Drive]" if doc.get('source_type') == 'google_drive' else "[Upload]"
            lines.append(
                f"  {i}. {source_icon} {doc['file_name']} "
                f"- {doc['num_chunks']} chunks "
                f"- {doc['uploaded_at']}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"list_documents error: {e}")
        return f"Loi khi lay danh sach: {e}"
