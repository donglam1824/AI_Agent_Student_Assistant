"""
Định nghĩa state cho Teams LangGraph agent.
"""
from typing import Annotated, List

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TeamsAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_request: str
    action_result: str
