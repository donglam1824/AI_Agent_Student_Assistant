"""
tools/doc_search/import_from_drive.py
---------------------------------------
LangChain tool: cho phép DocSearch Agent hướng dẫn người dùng
import tài liệu từ Google Drive vào hệ thống RAG.

Tool này KHÔNG tự động import (cần access_token của user).
Thay vào đó, nó trả về hướng dẫn rõ ràng cho user thực hiện
qua giao diện web, hoặc lấy danh sách drive docs đã import.
"""
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from services.doc_search_service import get_doc_search_service
from core.logger import logger


@tool
def list_drive_documents(config: RunnableConfig = None) -> str:
    """
    Liệt kê các tài liệu đã được import từ Google Drive vào hệ thống.
    Khác với list_documents (liệt kê TẤT CẢ), tool này chỉ hiển thị
    các tài liệu có nguồn gốc từ Google Drive.
    """
    service = get_doc_search_service()
    user_id = (config or {}).get("configurable", {}).get("user_id")
    try:
        all_docs = service.list_documents(user_id=user_id)
        drive_docs = [d for d in all_docs if d.get("source_type") == "google_drive"]

        if not drive_docs:
            return (
                "☁️ Chưa có tài liệu nào từ Google Drive.\n"
                "Để import, hãy vào trang **Quản lý Tài liệu** → tab **Google Drive** "
                "→ chọn file và nhấn 'Import vào ORCA'."
            )

        lines = ["☁️ Tài liệu đã import từ Google Drive:\n"]
        for i, doc in enumerate(drive_docs, 1):
            lines.append(
                f"  {i}. {doc['file_name']} "
                f"– {doc['num_chunks']} chunks "
                f"– Sync lần cuối: {doc['uploaded_at']}"
            )
        lines.append(
            "\n💡 Tip: Vào trang Tài liệu để sync lại nếu bạn đã chỉnh sửa file trên Drive."
        )
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"list_drive_documents error: {e}")
        return f"Loi khi lay danh sach Drive docs: {e}"


@tool
def guide_drive_import(file_description: str = "") -> str:
    """
    Cung cấp hướng dẫn cho người dùng khi họ muốn import tài liệu từ Google Drive.
    Gọi tool này khi người dùng đề cập đến Drive, tài liệu trên Drive, hoặc
    muốn tìm kiếm trong file Google Docs/Sheets/Slides của họ.

    Args:
        file_description: Mô tả file người dùng muốn import (tùy chọn).
    """
    hint = ""
    if file_description:
        hint = f'\n📎 File bạn muốn import: "{file_description}"'

    return (
        "☁️ **Import tài liệu từ Google Drive:**\n"
        f"{hint}\n"
        "Để đưa tài liệu từ Google Drive vào hệ thống tìm kiếm, hãy:\n\n"
        "1. Vào trang **Quản lý Tài liệu** (biểu tượng 📚 trên sidebar)\n"
        "2. Chọn tab **Google Drive**\n"
        "3. Browse thư mục và chọn file bạn muốn (PDF, DOCX, PPTX, Google Docs, Sheets, Slides)\n"
        "4. Nhấn nút **Import vào ORCA**\n\n"
        "Sau khi import xong, bạn có thể hỏi tôi về nội dung file đó!"
    )
