"""
tools/doc_search/upload_document.py
-------------------------------------
LangChain tool: upload và index tài liệu vào ChromaDB.
"""
from langchain_core.tools import tool
from services.doc_search_service import get_doc_search_service
from core.logger import logger


@tool
def upload_document(file_path: str) -> str:
    """
    Upload và lưu tài liệu vào hệ thống tìm kiếm.
    Hỗ trợ định dạng: PDF, DOCX, TXT.

    Args:
        file_path: Đường dẫn tuyệt đối đến file cần upload.
                   Ví dụ: C:/Users/user/Downloads/giai_tich.pdf
    """
    service = get_doc_search_service()
    try:
        return service.upload(file_path)
    except FileNotFoundError as e:
        return f"❌ Không tìm thấy file: {e}"
    except ValueError as e:
        return f"❌ Định dạng không hỗ trợ: {e}"
    except Exception as e:
        logger.error(f"upload_document error: {e}")
        return f"❌ Lỗi khi upload tài liệu: {e}"
