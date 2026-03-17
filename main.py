"""
main.py
-------
Entry point / interactive demo CLI for the AI Student Assistant.

Run:
    python main.py

This starts a simple REPL where you can chat with the CalendarAgent.
MOCK_GRAPH=True by default, so no Azure credentials needed for testing.
"""

from agents.calendar.agent import CalendarAgent
from core.logger import logger


WELCOME_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🎓 AI Student Assistant – Calendar Module           ║
║                      (Chế độ demo)                          ║
╚══════════════════════════════════════════════════════════════╝

Bạn có thể hỏi:
  • "Tôi có lịch gì trong tuần này?"
  • "Tạo lịch họp nhóm lúc 9h sáng mai"
  • "Xóa sự kiện [ID]"
  • "Cập nhật tiêu đề sự kiện [ID]"

Gõ 'quit' hoặc 'exit' để thoát.
"""


def main() -> None:
    logger.info("Starting AI Student Assistant – Calendar Module")
    print(WELCOME_BANNER)

    agent = CalendarAgent()

    while True:
        try:
            user_input = input("\n🧑‍🎓 Bạn: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nTạm biệt! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "thoát"}:
            print("Tạm biệt! 👋")
            break

        try:
            response = agent.run(user_input)
            print(f"\n🤖 Trợ lý: {response}")
        except Exception as e:
            logger.error(f"Agent error: {e}")
            print(f"\n❌ Lỗi: {e}")


if __name__ == "__main__":
    main()
