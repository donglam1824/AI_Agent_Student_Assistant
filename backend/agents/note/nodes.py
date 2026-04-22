"""
agents/note/nodes.py
--------------------
Node functions for the Note LangGraph agent.
"""

from langchain_core.messages import AIMessage
from agents.note.state import NoteAgentState
from core.logger import logger

def make_reason_node(llm_with_tools):
    """Factory: returns a `reason` node bound to the given LLM + tools."""

    def reason(state: NoteAgentState) -> dict:
        """
        Invoke the LLM to decide what action to take.
        """
        logger.debug("NoteAgent – reason node")
        response: AIMessage = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return reason


def should_continue(state: NoteAgentState) -> str:
    """
    Routing function: check if the last AI message contains tool calls.
    """
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        logger.debug("Routing → tools")
        return "tools"
    logger.debug("Routing → end")
    return "end"
