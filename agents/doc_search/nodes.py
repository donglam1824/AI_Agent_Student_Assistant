"""
agents/doc_search/nodes.py
---------------------------
Node functions cho DocSearch LangGraph agent.
"""
from langchain_core.messages import AIMessage
from agents.doc_search.state import DocSearchAgentState
from core.logger import logger


def make_reason_node(llm_with_tools):
    def reason(state: DocSearchAgentState) -> dict:
        logger.debug("DocSearchAgent – reason node")
        response: AIMessage = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}
    return reason


def should_continue(state: DocSearchAgentState) -> str:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        logger.debug("DocSearchAgent routing → tools")
        return "tools"
    logger.debug("DocSearchAgent routing → end")
    return "end"
