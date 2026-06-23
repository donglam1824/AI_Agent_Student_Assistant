"""
core/memory_manager.py
-----------------------
Convert DB chat history to LangChain messages with smart truncation.
"""
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from db.models import ChatMessage

# Defaults
MAX_HISTORY_TURNS = 10    # Giữ tối đa 10 cặp (user+assistant) = 20 messages
MAX_HISTORY_TOKENS = 4000 # Ước lượng, tránh chiếm quá nhiều context window


def build_history_messages(
    db_messages: list[ChatMessage],
    max_turns: int = MAX_HISTORY_TURNS,
) -> list[BaseMessage]:
    """
    Convert DB ChatMessage records → LangChain BaseMessage list.
    
    - Bỏ tin nhắn cuối (đó là tin nhắn mới, agent sẽ tự nhận qua HumanMessage)
    - Giữ tối đa `max_turns` cặp gần nhất
    - Output: [HumanMessage, AIMessage, HumanMessage, AIMessage, ...]
    """
    if not db_messages:
        return []
    
    # Bỏ tin nhắn mới nhất (user message hiện tại sẽ được truyền riêng)
    history = db_messages[:-1] if db_messages[-1].role == "user" else db_messages
    
    if not history:
        return []
    
    # Truncate: giữ max_turns * 2 messages gần nhất
    max_messages = max_turns * 2
    if len(history) > max_messages:
        history = history[-max_messages:]
    
    # Convert sang LangChain messages
    lc_messages: list[BaseMessage] = []
    for msg in history:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    
    return lc_messages
