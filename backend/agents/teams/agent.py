"""
agents/teams/agent.py
---------------------
TeamsAgent for reading Teams class updates, channel messages, and assignments.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.teams.nodes import make_reason_node, should_continue
from agents.teams.state import TeamsAgentState
from core.llm_manager import llm_manager
from core.logger import logger
from tools.teams.list_assignments import list_class_assignments
from tools.teams.list_channels import list_team_channels
from tools.teams.list_classes import list_education_classes
from tools.teams.list_messages import list_team_messages
from tools.teams.list_teams import list_teams


SYSTEM_PROMPT = """Ban la tro ly Microsoft Teams hoc tap cho sinh vien.
Ban giup sinh vien kiem tra lop hoc Teams, kenh, thong bao, tin nhan moi va bai tap.

Huong dan:
- Luon tra loi bang tieng Viet.
- Khi nguoi dung hoi ve lop Teams, hay dung list_teams.
- Khi can xem kenh cua mot lop, hay dung list_team_channels.
- Khi can xem thong bao hoac tin nhan moi, hay dung list_team_messages.
- Khi can xem danh sach lop Education hoac can class_id, hay dung list_education_classes.
- Khi can xem bai tap, deadline, nhiem vu tren Teams/Classroom, hay dung list_class_assignments.
- Neu chua co team_id, channel_id hoac class_id, hay dung tool lay danh sach Teams/kenh/lop truoc.
- Chi tom tat thong tin quan trong cho sinh vien: mon/lop, nguoi gui, thoi gian, deadline va viec can lam.
- Thoi gian hien tai: {current_time}
"""


TEAMS_TOOLS = [
    list_teams,
    list_team_channels,
    list_education_classes,
    list_team_messages,
    list_class_assignments,
]


class TeamsAgent:
    """LangGraph-based Teams Agent."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._llm_with_tools = llm_manager.get_with_tools(
            task="teams",
            tools=TEAMS_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(f"TeamsAgent initialized for user={user_id}")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(TeamsAgentState)
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(TEAMS_TOOLS))
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

        initial_state: TeamsAgentState = {
            "messages": messages,
            "user_request": user_message,
            "action_result": "",
        }

        config = {"configurable": {"user_id": self._user_id}}
        logger.info(f"TeamsAgent.run - user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return final_state["messages"][-1].content
