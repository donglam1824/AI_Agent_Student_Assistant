"""
agents/email/agent.py
---------------------
EmailAgent - LangGraph ReAct-style agent for Gmail and Outlook operations.
Ưu tiên luồng học thuật: lọc → phân tích ưu tiên → trình bày có cấu trúc.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.email.nodes import make_reason_node, should_continue
from agents.email.state import EmailAgentState
from agents.email.tools.analyze_priority import analyze_priority
from agents.email.tools.create_reminder import create_reminder
from agents.email.tools.extract_deadline import extract_deadline
from core.llm_manager import llm_manager
from core.logger import logger
from tools.email.list_emails import list_emails
from tools.email.reply_email import reply_email
from tools.email.scan_and_summarize import scan_and_summarize_emails
from tools.email.read_email_detail import read_email_detail
from tools.email.send_email import send_email


SYSTEM_PROMPT = """Ban la tro ly email hoc thuat thong minh danh cho sinh vien.
Ban giup sinh vien quan ly ca Gmail va Outlook, doc email tu giang vien/nha truong,
soan email hoc thuat va tra loi email.

Huong dan uu tien (PHAI tuan thu):
1. Khi nguoi dung yeu cau "kiem tra email", "email moi", "xem hop thu", "co email gi moi khong":
   → LUON goi scan_and_summarize_emails TRUOC.
   → Tool nay tu dong loc chi email hoc thuat, phan loai uu tien, va trinh bay co cau truc.
   → KHONG BAO GIO dump danh sach email tho. Khong hien body_preview tru khi nguoi dung yeu cau cu the.

2. Khi nguoi dung muon doc chi tiet 1 email cu the (vi du: "doc email cua thay Nguyen", "xem email thu 2"):
   → Goi read_email_detail voi message_id tuong ung.
   → Tool nay se tom tat noi dung, trich xuat deadline, va goi y hanh dong.

3. Khi nguoi dung yeu cau xem TAT CA email (ke ca khong hoc thuat):
   → Goi list_emails voi academic_only=False.

4. Khi nguoi dung chi ro Gmail hoac Outlook, dung source="gmail" hoac source="outlook".

5. Email ID tu scan_and_summarize_emails hoac list_emails co dang gmail:<id> hoac outlook:<id>.
   Khi tra loi email, truyen nguyen ID nay cho reply_email.

6. Khi gui email moi, neu nguoi dung khong chi ro hop thu gui, dung source mac dinh "gmail".

7. Khi soan email, dung giong van lich su, trang trong va phu hop moi truong hoc thuat.
   Vi du: xin phep nghi hoc, hoi bai giang vien, phan hoi phong dao tao.

8. Khi phat hien deadline trong email, CHU DONG de xuat tao nhac lich bang create_reminder.

9. Khi email can phan hoi (priority = follow_up hoac urgent), CHU DONG de xuat soan email tra loi.

10. Luon xac nhan noi dung email voi nguoi dung truoc khi gui hoac tra loi.

11. Luon tra loi bang tieng Viet.

12. Thoi gian hien tai: {current_time}
"""


EMAIL_TOOLS = [
    scan_and_summarize_emails,  # Ưu tiên: quét + lọc học thuật + phân loại ưu tiên
    read_email_detail,          # Đọc chi tiết 1 email + tóm tắt + deadline
    list_emails,                # Fallback: xem tất cả email
    send_email,
    reply_email,
    analyze_priority,
    extract_deadline,
    create_reminder,
]


class EmailAgent:
    """LangGraph-based Email Agent with multi-mailbox support."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._llm_with_tools = llm_manager.get_with_tools(
            task="email",
            tools=EMAIL_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(f"EmailAgent initialized for user={user_id}")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(EmailAgentState)
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(EMAIL_TOOLS))
        builder.add_edge(START, "reason")
        builder.add_conditional_edges(
            "reason",
            should_continue,
            {"tools": "tools", "end": END},
        )
        builder.add_edge("tools", "reason")
        return builder.compile()

    def run(self, user_message: str) -> str:
        from datetime import datetime, timezone

        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        initial_state: EmailAgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time)),
                HumanMessage(content=user_message),
            ],
            "user_request": user_message,
            "action_result": "",
        }

        config = {"configurable": {"user_id": self._user_id}}

        logger.info(f"EmailAgent.run - user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return final_state["messages"][-1].content
