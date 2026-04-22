"""
tools/doc_search/search_documents.py
--------------------------------------
LangChain tool: tìm kiếm tài liệu theo ngữ nghĩa.
Có hỗ trợ metadata filter.
"""
from typing import Optional
from langchain_core.tools import tool
from services.doc_search_service import get_doc_search_service
from core.logger import logger


@tool
def search_documents(query: str, document_name: Optional[str] = None) -> str:
    """
    Tìm kiếm thông tin trong các tài liệu đã upload theo ngữ nghĩa.
    Trả về các đoạn văn liên quan nhất từ tài liệu. Có thể lọc theo tên file.

    Args:
        query: Câu hỏi hoặc từ khóa cần tìm.
               Ví dụ: "đạo hàm hàm hợp", "B-Tree index", "định nghĩa recursion"
        document_name: (Tuỳ chọn) Tên file cụ thể muốn tìm kiếm trong đó.
               Ví dụ: "giai_tich_co_ban.txt"
    """
    service = get_doc_search_service()
    try:
        return service.search(query, document_name=document_name)
    except Exception as e:
        logger.error(f"search_documents error: {e}")
        return f"❌ Lỗi khi tìm kiếm: {e}"
