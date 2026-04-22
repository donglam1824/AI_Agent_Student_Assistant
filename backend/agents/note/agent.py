"""
agents/note/agent.py
--------------------
NoteAgent – LangGraph ReAct-style agent for note operations.
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

Hướng dẫn:
- Luôn trả lời bằng tiếng Việt.
- Khi cần thao tác ghi chú, hãy sử dụng các tool được cung cấp.
- Khi người dùng muốn xem ghi chú, hãy dùng list_notes.
- Khi người dùng muốn lưu thông tin (bài giảng, deadline, bài tập, ý tưởng), hãy dùng create_note.
- Tự động đặt tiêu đề ghi chú rõ ràng nếu người dùng không đề cập (ví dụ: "Ghi chú môn Toán – 22/04").
- Luôn xác nhận lại với người dùng sau khi tạo ghi chú.
- Ghi chú được lưu cục bộ trong cơ sở dữ liệu, không cần kết nối cloud.
- Thời gian hiện tại: {current_time}
"""

NOTE_TOOLS = [
    list_notes,
    create_note,
]


class NoteAgent:
    """
    LangGraph-based Note Agent.
    """

    def __init__(self) -> None:
        self._llm_with_tools = llm_manager.get_with_tools(
            task="note",
            tools=NOTE_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(
            f"NoteAgent initialized – LLM info: {llm_manager.info()}"
        )

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(NoteAgentState)

        # Nodes
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(NOTE_TOOLS))

        # Edges
        builder.add_edge(START, "reason")
        builder.add_conditional_edges(
            "reason",
            should_continue,
            {"tools": "tools", "end": END},
        )
        builder.add_edge("tools", "reason")  # loop back to reason after tool use

        return builder.compile()

    def run(self, user_message: str) -> str:
        """
        Run the agent with a user message.
        """
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        initial_state: NoteAgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time)),
                HumanMessage(content=user_message),
            ],
            "user_request": user_message,
            "action_result": "",
        }

        logger.info(f"NoteAgent.run – query: {user_message!r}")
        final_state = self._graph.invoke(initial_state)

        # Last message from AI (no tool_calls)
        response = final_state["messages"][-1].content
        return response
