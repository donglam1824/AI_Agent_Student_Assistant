import pytest
from langchain_core.messages import HumanMessage, AIMessage
from core.memory_manager import build_history_messages
from db.models import ChatMessage

def test_build_history_messages_empty():
    assert build_history_messages([]) == []

def test_build_history_messages_removes_last_user_message():
    messages = [
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
        ChatMessage(role="user", content="how are you?")
    ]
    lc_messages = build_history_messages(messages, max_turns=10)
    assert len(lc_messages) == 2
    assert isinstance(lc_messages[0], HumanMessage)
    assert lc_messages[0].content == "hello"
    assert isinstance(lc_messages[1], AIMessage)
    assert lc_messages[1].content == "hi"

def test_build_history_messages_keeps_last_if_assistant():
    messages = [
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
    ]
    lc_messages = build_history_messages(messages, max_turns=10)
    assert len(lc_messages) == 2
    assert lc_messages[0].content == "hello"
    assert lc_messages[1].content == "hi"

def test_build_history_messages_truncation():
    # Create 30 messages (15 user, 15 assistant)
    messages = []
    for i in range(15):
        messages.append(ChatMessage(role="user", content=f"user_{i}"))
        messages.append(ChatMessage(role="assistant", content=f"assistant_{i}"))
        
    messages.append(ChatMessage(role="user", content="user_15")) # last one, should be removed
    
    # max_turns=10 means max 20 messages. So it should keep indices from 10 to 29
    lc_messages = build_history_messages(messages, max_turns=10)
    assert len(lc_messages) == 20
    assert lc_messages[0].content == "user_5"
    assert lc_messages[-1].content == "assistant_14"

def test_build_history_messages_no_history_after_truncate():
    messages = [
        ChatMessage(role="user", content="hello")
    ]
    lc_messages = build_history_messages(messages)
    assert lc_messages == []
