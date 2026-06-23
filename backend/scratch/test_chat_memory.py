import os
import sys
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import SessionLocal, init_db
from db.models import User, ChatMessage
from db import crud
from core.memory_manager import build_history_messages
from agents.doc_search.agent import DocSearchAgent

def test_memory():
    init_db()
    db = SessionLocal()
    
    # Setup mock user
    user = db.query(User).filter(User.email == "test_memory@example.com").first()
    if not user:
        user = User(email="test_memory@example.com", name="Test Memory")
        db.add(user)
        db.commit()
        db.refresh(user)

    chat = crud.create_chat(db, user.id)
    chat_id = chat.id
    
    agent = DocSearchAgent(user_id=user.id)
    
    print(f"--- Bắt đầu test trực tiếp bộ nhớ (Chat ID: {chat_id}) ---")

    # Lượt 1
    msg1 = "Xin chào, tôi tên là Hải. Tí nữa nếu tôi hỏi thì nhớ tên tôi nhé."
    print(f"\n[User]: {msg1}")
    
    # Không có history ở lượt 1
    resp1 = agent.run(msg1)
    print(f"[Agent]: {resp1}")
    
    # Lưu vào DB để giả lập luồng thực tế
    crud.add_message(db, chat_id, "user", msg1)
    crud.add_message(db, chat_id, "assistant", resp1)

    # Lượt 2
    msg2 = "Tôi tên là gì?"
    print(f"\n[User]: {msg2}")
    
    # Tải history
    db_messages = crud.get_chat_messages(db, chat_id)
    chat_history = build_history_messages(db_messages)
    
    resp2 = agent.run(msg2, chat_history=chat_history)
    print(f"[Agent]: {resp2}")

if __name__ == "__main__":
    test_memory()
