"""
agents/calendar/agent.py
-------------------------
CalendarAgent – LangGraph ReAct-style agent for calendar operations.

Graph topology:
  START
    ↓
  [reason]  ←────────────────┐
    ↓ (tool_calls?)          │
  [tools]  ──────────────────┘  (loop until no tool calls)
    ↓ (no tool_calls)
  END

Usage:
    agent = CalendarAgent()
    response = agent.run("Tôi có lịch gì trong tuần này?")
    print(response)
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.calendar.nodes import make_reason_node, should_continue
from agents.calendar.state import CalendarAgentState
from config.settings import settings
from core.llm_manager import llm_manager
from core.logger import logger
from tools.calendar.list_events import list_calendar_events
from tools.calendar.create_event import create_calendar_event
from tools.calendar.update_event import update_calendar_event
from tools.calendar.delete_event import delete_calendar_event

SYSTEM_PROMPT = """Bạn là trợ lý quản lý lịch học thông minh dành cho sinh viên.
Bạn giúp sinh viên xem, tạo, sửa và xóa các sự kiện trên Google Calendar liên quan đến học tập.

Hướng dẫn:
- Luôn trả lời bằng tiếng Việt.
- Khi cần thao tác lịch, hãy sử dụng các tool được cung cấp.
- Khi người dùng hỏi về sự kiện, hãy dùng list_calendar_events trước.
- Luôn xác nhận lại với người dùng sau khi tạo/sửa/xóa sự kiện.
- Bối cảnh: lịch học, lịch ôn thi, lịch họp nhóm, lịch nộp bài, lịch gặp giảng viên.
- Khi tạo sự kiện, hãy sử dụng timezone Asia/Ho_Chi_Minh.
- Thời gian hiện tại: {current_time}
"""

CALENDAR_TOOLS = [
    list_calendar_events,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
]


class CalendarAgent:
    """
    LangGraph-based Calendar Agent.

    Extend this pattern for other modules (NotesAgent, EmailAgent, etc.)
    by following the same agents/<module>/ structure.
    """

    def __init__(self) -> None:
        self._llm_with_tools = llm_manager.get_with_tools(
            task="calendar",
            tools=CALENDAR_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(
            f"CalendarAgent initialized – LLM info: {llm_manager.info()}"
        )

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(CalendarAgentState)

        # Nodes
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(CALENDAR_TOOLS))

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

        Args:
            user_message: Natural language request from the student.

        Returns:
            Agent's final response as a string.
        """
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        initial_state: CalendarAgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time)),
                HumanMessage(content=user_message),
            ],
            "user_request": user_message,
            "action_result": "",
        }

        logger.info(f"CalendarAgent.run – query: {user_message!r}")
        final_state = self._graph.invoke(initial_state)

        # Last message from AI (no tool_calls)
        response = final_state["messages"][-1].content
        return response
