"""
Chuyển đổi lịch sử chat từ DB sang tin nhắn LangChain kèm giới hạn turns.
"""
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from db.models import ChatMessage

MAX_HISTORY_TURNS = 10    # Max 10 lượt hội thoại (20 tin nhắn)
MAX_HISTORY_TOKENS = 4000 


def build_history_messages(
    db_messages: list[ChatMessage],
    max_turns: int = MAX_HISTORY_TURNS,
) -> list[BaseMessage]:
    """Chuyển ChatMessage trong DB thành BaseMessage của LangChain"""
    if not db_messages:
        return []
    
    # Bỏ tin nhắn cuối nếu là user message mới
    history = db_messages[:-1] if db_messages[-1].role == "user" else db_messages
    
    if not history:
        return []
    
    # Lấy tối đa số tin nhắn giới hạn gần nhất
    max_messages = max_turns * 2
    if len(history) > max_messages:
        history = history[-max_messages:]
    
    lc_messages: list[BaseMessage] = []
    for msg in history:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    
    return lc_messages
