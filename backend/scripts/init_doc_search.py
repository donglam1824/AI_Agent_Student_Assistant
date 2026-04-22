"""
scripts/init_doc_search.py
---------------------------
Chạy 1 lần để nạp sample docs vào ChromaDB.
Usage: python scripts/init_doc_search.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.doc_search_service import get_doc_search_service

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample_docs"

def main():
    service = get_doc_search_service()
    sample_files = list(SAMPLE_DIR.glob("*.txt")) + list(SAMPLE_DIR.glob("*.pdf"))
    
    if not sample_files:
        print("Không tìm thấy file mẫu hợp lệ.")
        return

    for file_path in sample_files:
        print(f"Đang nạp: {file_path.name}...")
        result = service.upload(str(file_path))
        print(result)
    
    print(f"\n✅ Hoàn thành! {len(sample_files)} tài liệu mẫu đã được nạp.")
    print("Bạn có thể chạy: python main.py để bắt đầu RAG.")

if __name__ == "__main__":
    main()
