"""
main.py
-------
Entry point / interactive demo CLI for the AI Student Assistant.

Run:
    python main.py

This starts a simple REPL where you can chat with the CalendarAgent.
MOCK_GRAPH=True by default, so no Azure credentials needed for testing.
"""

from typing import Optional

from agents.calendar.agent import CalendarAgent
from agents.note.agent import NoteAgent
from core.llm_manager import llm_manager
from core.logger import logger


WELCOME_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🎓 AI Student Assistant – Muti-Agent Demo           ║
║   (Hỗ trợ Lịch học, Ghi chú cá nhân, Email và Tìm tài liệu)  ║
╚══════════════════════════════════════════════════════════════╝

Bạn có thể hỏi bất kỳ chủ đề nào:
  • "Tôi có lịch gì trong tuần này?" (Calendar)
  • "Tạo ghi chú về buổi học Toán lúc 9h" (Note)
  • "Kiểm tra hộp thư của tôi có email mới không?" (Email)
  • "Tìm tài liệu về đạo hàm trong file giải tích" (DocSearch)

Gõ 'quit' hoặc 'exit' để thoát.
"""

def classify_intent(text: str) -> str:
    """
    Sử dụng LLM mặc định để phân tích câu hỏi người dùng và trả về 1 trong 4 nhãn:
    'calendar', 'note', 'email', 'unknown'
    """
    llm = llm_manager.get("default")
    prompt = (
        "Bạn là một bộ định tuyến cực kỳ chính xác.\n"
        "Hãy phân tích câu sau của người dùng và xếp nó vào 1 trong 4 nhóm chức năng:\n"
        "1. 'calendar': Các câu hỏi liên quan đến lịch trình, thời gian biểu, hẹn hò, cuộc họp, sự kiện, dời lịch...\n"
        "2. 'note': Các câu hỏi về việc ghi chép, tạo ghi chú lưu trữ, xem các ghi chú cũ, tóm tắt bài giảng...\n"
        "3. 'email': Các câu hỏi yêu cầu soạn thư, gửi email, kiểm tra hòm thư, xử lý thư phản hồi...\n"
        "4. 'docsearch': Tìm kiếm tài liệu, hỏi đáp kiến thức từ tệp tải lên, quản lý tài liệu (PDF, TXT, DOCX)...\n"
        "Nếu không liên quan hoặc không thể xác định, hãy trả về 'unknown'.\n\n"
        f"Câu hỏi: \"{text}\"\n"
        "CHỈ trả về ĐÚNG 1 TỪ DUY NHẤT (lowercase) thuộc: [calendar, note, email, docsearch, unknown]."
    )
    
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()
    
    # Validation
    if "calendar" in intent:
        return "calendar"
    if "note" in intent:
        return "note"
    if "email" in intent:
        return "email"
    if "docsearch" in intent or "search" in intent or "tài liệu" in text.lower():
        return "docsearch"
    return "unknown"


def main() -> None:
    logger.info("Starting AI Student Assistant – Multi-Agent Demo")
    print(WELCOME_BANNER)

    print("Đang khởi tạo các tác vụ thường xuyên (Lịch, Ghi chú)...")
    calendar_agent = CalendarAgent()
    note_agent = NoteAgent()
    
    # Khởi tạo Email Agent và DocSearch Agent theo cơ chế Lazy-load
    email_agent: Optional['EmailAgent'] = None
    doc_search_agent: Optional['DocSearchAgent'] = None
    print("Sẵn sàng!\n" + "-" * 62)

    while True:
        try:
            user_input = input("\n🧑‍🎓 Bạn: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nTạm biệt! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "thoát"}:
            print("\nTạm biệt! 👋")
            break

        try:
            print("🤖 Trợ lý: Đang phân tích yêu cầu...")
            intent = classify_intent(user_input)
            
            if intent == "calendar":
                response = calendar_agent.run(user_input)
                print(f"🤖 Trợ lý (Lịch): {response}")
                
            elif intent == "note":
                response = note_agent.run(user_input)
                print(f"🤖 Trợ lý (Ghi chú): {response}")
                
            elif intent == "email":
                if email_agent is None:
                    print("🤖 Trợ lý: Chờ chút, mình đang đánh thức Email Agent...")
                    from agents.email.agent import EmailAgent
                    email_agent = EmailAgent()
                response = email_agent.run(user_input)
                print(f"🤖 Trợ lý (Email): {response}")

            elif intent == "docsearch":
                if doc_search_agent is None:
                    print("🤖 Trợ lý: Đang mở Module Tìm kiếm Tài liệu...")
                    from agents.doc_search.agent import DocSearchAgent
                    doc_search_agent = DocSearchAgent()
                response = doc_search_agent.run(user_input)
                print(f"🤖 Trợ lý (Tài liệu): {response}")
                
            else:
                print("🤖 Trợ lý: Xin lỗi, mình chưa hiểu rõ yêu cầu. Bạn có thể nói rõ hơn về việc Lịch học, Ghi chú, Email hoặc Tài liệu không?")
                
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            print(f"\n❌ Lỗi: {e}")


if __name__ == "__main__":
    main()
