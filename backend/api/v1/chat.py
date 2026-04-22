"""
api/v1/chat.py
--------------
Chat endpoint with Server-Sent Events (SSE) streaming.
  - POST /chat          → Send message, receive SSE stream
  - GET  /chat/history  → List user's chats
  - GET  /chat/{id}     → Get chat messages
  - DELETE /chat/{id}   → Delete a chat
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import User
from api.deps import get_current_user
from core.logger import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Request / Response Models ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None  # None = new chat


class ChatSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    agent: Optional[str] = None
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────

def _classify_intent(text: str) -> str:
    """Classify user intent using LLM. Reuses logic from main.py."""
    from core.llm_manager import llm_manager
    llm = llm_manager.get("default")
    prompt = (
        "Bạn là một bộ định tuyến cực kỳ chính xác.\n"
        "Hãy phân tích câu sau của người dùng và xếp nó vào 1 trong 4 nhóm chức năng:\n"
        "1. 'calendar': Các câu hỏi liên quan đến lịch trình, thời gian biểu, hẹn hò, cuộc họp, sự kiện, dời lịch...\n"
        "2. 'note': Các câu hỏi về việc ghi chép, tạo ghi chú lưu trữ, xem các ghi chú cũ, tóm tắt bài giảng...\n"
        "3. 'email': Các câu hỏi yêu cầu soạn thư, gửi email, kiểm tra hòm thư, xử lý thư phản hồi...\n"
        "4. 'docsearch': Tìm kiếm tài liệu, hỏi đáp kiến thức từ tệp tải lên, quản lý tài liệu (PDF, TXT, DOCX)...\n"
        "Nếu không liên quan hoặc không thể xác định, hãy trả về 'unknown'.\n\n"
        f"Câu hỏi: \"{text}\"\n"
        "CHỈ trả về ĐÚNG 1 TỪ DUY NHẤT (lowercase) thuộc: [calendar, note, email, docsearch, unknown]."
    )
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()

    if "calendar" in intent:
        return "calendar"
    if "note" in intent:
        return "note"
    if "email" in intent:
        return "email"
    if "docsearch" in intent or "search" in intent:
        return "docsearch"
    return "unknown"


def _get_agent(intent: str):
    """Lazy-load the appropriate agent based on intent."""
    if intent == "calendar":
        from agents.calendar.agent import CalendarAgent
        return CalendarAgent()
    elif intent == "note":
        from agents.note.agent import NoteAgent
        return NoteAgent()
    elif intent == "email":
        from agents.email.agent import EmailAgent
        return EmailAgent()
    elif intent == "docsearch":
        from agents.doc_search.agent import DocSearchAgent
        return DocSearchAgent()
    return None


async def _stream_chat(user_input: str, chat_id: str, user_id: str, db: Session):
    """
    Generator that yields SSE events:
      event: agent   → { "agent": "calendar" }
      event: token   → { "content": "..." }
      event: done    → { "chat_id": "..." }
      event: error   → { "message": "..." }
    """
    try:
        # Classify intent
        intent = _classify_intent(user_input)

        # Send agent event
        yield f"event: agent\ndata: {json.dumps({'agent': intent})}\n\n"

        # Get response from agent
        agent = _get_agent(intent)
        if agent is None:
            response_text = "Xin lỗi, mình chưa hiểu rõ yêu cầu. Bạn có thể nói rõ hơn về Lịch học, Ghi chú, Email hoặc Tài liệu không?"
        else:
            response_text = agent.run(user_input)

        # Stream response token by token (simulate streaming for non-streaming agents)
        # Split into words for natural typing effect
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'content': chunk})}\n\n"

        # Save messages to DB
        crud.add_message(db, chat_id, "user", user_input)
        crud.add_message(db, chat_id, "assistant", response_text, agent=intent)

        # Auto-generate chat title from first message
        chat = crud.get_chat_by_id(db, chat_id)
        if chat and chat.title == "Cuộc trò chuyện mới":
            # Use first 50 chars of user input as title
            chat.title = user_input[:50] + ("..." if len(user_input) > 50 else "")
            db.commit()

        yield f"event: done\ndata: {json.dumps({'chat_id': chat_id})}\n\n"

    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("")
async def send_message(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a chat message and receive an SSE stream response.
    If chat_id is None, a new chat is created.
    """
    # Create or get chat
    if body.chat_id:
        chat = crud.get_chat_by_id(db, body.chat_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Chat không tồn tại.")
        chat_id = chat.id
    else:
        chat = crud.create_chat(db, current_user.id)
        chat_id = chat.id

    return StreamingResponse(
        _stream_chat(body.message, chat_id, current_user.id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=list[ChatSummary])
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all chats for the current user."""
    chats = crud.get_user_chats(db, current_user.id)
    return [
        ChatSummary(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in chats
    ]


@router.get("/{chat_id}", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all messages in a specific chat."""
    chat = crud.get_chat_by_id(db, chat_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat không tồn tại.")

    messages = crud.get_chat_messages(db, chat_id)
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            agent=m.agent,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a chat and all its messages."""
    chat = crud.get_chat_by_id(db, chat_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat không tồn tại.")
    crud.delete_chat(db, chat_id)
    return {"message": "Đã xóa cuộc trò chuyện."}
