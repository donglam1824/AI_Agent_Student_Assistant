"""
Các nodes cho Email LangGraph agent.
"""

from langchain_core.messages import AIMessage
from agents.email.state import EmailAgentState
from core.logger import logger

def make_reason_node(llm_with_tools):

    def reason(state: EmailAgentState) -> dict:
        logger.debug("EmailAgent – reason node")
        response: AIMessage = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return reason


def should_continue(state: EmailAgentState) -> str:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        logger.debug("Routing → tools")
        return "tools"
    logger.debug("Routing → end")
    return "end"
