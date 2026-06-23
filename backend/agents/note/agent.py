"""
agents/note/agent.py
--------------------
NoteAgent – LangGraph ReAct-style agent for note operations.
Nhận user_id và inject vào RunnableConfig khi invoke graph.
Ghi chú được lưu qua Google Tasks (ORCA Notes tasklist).
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.note.nodes import make_reason_node, should_continue
from agents.note.state import NoteAgentState
from core.llm_manager import llm_manager
from core.logger import logger
from tools.note.list_notes import list_notes
from tools.note.create_note import create_note

SYSTEM_PROMPT = """Bạn là trợ lý ghi chú học tập thông minh dành cho sinh viên.
Bạn giúp sinh viên ghi chép, quản lý và tra cứu các ghi chú liên quan đến việc học.
Ghi chú được lưu trữ trên Google Tasks (danh sách ORCA Notes) của tài khoản Google của bạn.

Hướng dẫn:
- Luôn trả lời bằng tiếng Việt.
- Khi cần thao tác ghi chú, hãy sử dụng các tool được cung cấp.
- Khi người dùng muốn xem ghi chú, hãy dùng list_notes.
- Khi người dùng muốn lưu thông tin (bài giảng, deadline, bài tập, ý tưởng), hãy dùng create_note.
- Tự động đặt tiêu đề ghi chú rõ ràng nếu người dùng không đề cập (ví dụ: "Ghi chú môn Toán – 22/04").
- Luôn xác nhận lại với người dùng sau khi tạo ghi chú.
- Thời gian hiện tại: {current_time}
"""

NOTE_TOOLS = [
    list_notes,
    create_note,
]


class NoteAgent:
    """LangGraph-based Note Agent – hỗ trợ đa người dùng qua user_id."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._llm_with_tools = llm_manager.get_with_tools(
            task="note",
            tools=NOTE_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(f"NoteAgent initialized for user={user_id}")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(NoteAgentState)
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(NOTE_TOOLS))
        builder.add_edge(START, "reason")
        builder.add_conditional_edges(
            "reason",
            should_continue,
            {"tools": "tools", "end": END},
        )
        builder.add_edge("tools", "reason")
        return builder.compile()

    def run(self, user_message: str, chat_history: list | None = None) -> str:
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        messages = [SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time))]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=user_message))

        initial_state: NoteAgentState = {
            "messages": messages,
            "user_request": user_message,
            "action_result": "",
        }

        config = {"configurable": {"user_id": self._user_id}}

        logger.info(f"NoteAgent.run – user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return final_state["messages"][-1].content
