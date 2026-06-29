"""
Định nghĩa state cho Calendar LangGraph agent.
"""

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CalendarAgentState(TypedDict):
    """Trạng thái truyền nhận giữa các node trong Calendar agent graph"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_request: str
    action_result: str
