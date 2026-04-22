"""
agents/doc_search/state.py
---------------------------
TypedDict state cho DocSearch LangGraph agent.
"""
from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class DocSearchAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_request: str
    action_result: str
