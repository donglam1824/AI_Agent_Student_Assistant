"""
agents/email/agent.py
---------------------
EmailAgent – LangGraph ReAct-style agent for email operations.
Nhận user_id và inject vào RunnableConfig khi invoke graph.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.email.nodes import make_reason_node, should_continue
from agents.email.state import EmailAgentState
from core.llm_manager import llm_manager
from core.logger import logger
from tools.email.list_emails import list_emails
from tools.email.send_email import send_email
from agents.email.tools.analyze_priority import analyze_priority
from agents.email.tools.extract_deadline import extract_deadline
from agents.email.tools.create_reminder import create_reminder

SYSTEM_PROMPT = """Bạn là trợ lý email học thuật thông minh dành cho sinh viên.
Bạn giúp sinh viên quản lý hộp thư, đọc email từ giảng viên/nhà trường, và soạn email học thuật.

Hướng dẫn:
- Luôn trả lời bằng tiếng Việt.
- Khi cần thao tác email, hãy sử dụng các tool được cung cấp.
- Khi người dùng hỏi về email mới, hãy dùng list_emails.
- Khi soạn email, hãy dùng giọng văn lịch sự, trang trọng phù hợp với môi trường học thuật.
- Ví dụ email học thuật: xin phép nghỉ học, hỏi bài giảng viên, phản hồi phòng đào tạo.
- Luôn xác nhận nội dung email với người dùng trước khi gửi.
- Thời gian hiện tại: {current_time}
"""

EMAIL_TOOLS = [
    list_emails,
    send_email,
    analyze_priority,
    extract_deadline,
    create_reminder,
]


class EmailAgent:
    """LangGraph-based Email Agent – hỗ trợ đa người dùng qua user_id."""

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

        logger.info(f"EmailAgent.run – user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return final_state["messages"][-1].content
