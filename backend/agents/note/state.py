"""
agents/note/state.py
--------------------
TypedDict state for the Note LangGraph agent.
"""

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class NoteAgentState(TypedDict):
    """
    State object passed between nodes in the Note agent graph.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    user_request: str
    action_result: str
