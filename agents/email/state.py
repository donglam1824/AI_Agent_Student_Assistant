"""
agents/email/state.py
---------------------
TypedDict state for the Email LangGraph agent.
"""

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class EmailAgentState(TypedDict):
    """
    State object passed between nodes in the Email agent graph.

    - messages:      Full conversation history (auto-appended via add_messages reducer)
    - user_request:  The latest user message text (for quick access in nodes)
    - action_result: Result string from the last tool execution
    """
    messages: Annotated[List[BaseMessage], add_messages]
    user_request: str
    action_result: str
