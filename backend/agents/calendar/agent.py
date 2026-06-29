"""
Agent quản lý lịch học (Google Calendar) sử dụng LangGraph.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.calendar.nodes import make_reason_node, should_continue
from agents.calendar.state import CalendarAgentState
from config.settings import settings
from core.llm_manager import llm_manager, coerce_message_content
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

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._llm_with_tools = llm_manager.get_with_tools(
            task="calendar",
            tools=CALENDAR_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(f"CalendarAgent initialized for user={user_id}")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(CalendarAgentState)
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(CALENDAR_TOOLS))
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

        initial_state: CalendarAgentState = {
            "messages": messages,
            "user_request": user_message,
            "action_result": "",
        }

        # Truyền user_id qua config cho các tools
        config = {"configurable": {"user_id": self._user_id}}

        logger.info(f"CalendarAgent.run – user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return coerce_message_content(final_state["messages"][-1].content)
