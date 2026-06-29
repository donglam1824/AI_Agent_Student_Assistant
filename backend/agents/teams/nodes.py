"""
Các nodes cho Teams LangGraph agent.
"""

from langchain_core.messages import AIMessage

from agents.teams.state import TeamsAgentState
from core.logger import logger


def make_reason_node(llm_with_tools):
    def reason(state: TeamsAgentState) -> dict:
        logger.debug("TeamsAgent - reason node")
        response: AIMessage = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return reason


def should_continue(state: TeamsAgentState) -> str:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        logger.debug("TeamsAgent routing -> tools")
        return "tools"
    logger.debug("TeamsAgent routing -> end")
    return "end"
