"""
agents/calendar/nodes.py
-------------------------
Node functions for the Calendar LangGraph agent.

Graph flow:
  START → reason → (tool_node if tools called) → respond → END
                ↑___________________________|
"""

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from agents.calendar.state import CalendarAgentState
from core.logger import logger


def make_reason_node(llm_with_tools):
    """Factory: returns a `reason` node bound to the given LLM + tools."""

    def reason(state: CalendarAgentState) -> dict:
        """
        Invoke the LLM to decide what action to take.
        The LLM can either call a tool OR respond directly.
        """
        logger.debug("CalendarAgent – reason node")
        response: AIMessage = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return reason


def should_continue(state: CalendarAgentState) -> str:
    """
    Routing function: check if the last AI message contains tool calls.
    Returns 'tools' or 'end'.
    """
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        logger.debug("Routing → tools")
        return "tools"
    logger.debug("Routing → end")
    return "end"
