"""
Định nghĩa state cho Email LangGraph agent.
"""

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class EmailAgentState(TypedDict):
    """Trạng thái truyền nhận giữa các node trong Email agent graph"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_request: str
    action_result: str
