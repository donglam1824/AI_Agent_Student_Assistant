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
import re
import unicodedata
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import Document, User
from api.deps import get_current_user
from core.logger import logger
from services.intent_router import IntentRouter

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Request / Response Models ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None  # None = new chat
    source_scope: Optional[Dict[str, Any]] = None


class ChatSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    source_scope: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    agent: Optional[str] = None
    source_scope: Optional[Dict[str, Any]] = None
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────



def _parse_source_scope(raw_scope: Optional[str | Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not raw_scope:
        return None
    if isinstance(raw_scope, dict):
        return raw_scope
    try:
        parsed = json.loads(raw_scope)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _source_scope_to_json(source_scope: Optional[Dict[str, Any]]) -> Optional[str]:
    if not source_scope or source_scope.get("mode") == "all":
        return None
    return json.dumps(source_scope, ensure_ascii=False)


def _normalize_source_scope(
    db: Session,
    user_id: str,
    source_scope: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not source_scope or source_scope.get("mode") == "all":
        return None

    mode = source_scope.get("mode")
    if mode == "documents":
        requested_ids = source_scope.get("document_ids") or []
        document_ids = []
        seen = set()
        for doc_id in requested_ids:
            if isinstance(doc_id, str) and doc_id and doc_id not in seen:
                document_ids.append(doc_id)
                seen.add(doc_id)
        if not document_ids:
            raise HTTPException(status_code=400, detail="Chua chon tai lieu nao.")

        owned_docs = (
            db.query(Document)
            .filter(Document.user_id == user_id, Document.id.in_(document_ids))
            .all()
        )
        owned_ids = {doc.id for doc in owned_docs}
        if len(owned_ids) != len(document_ids):
            raise HTTPException(status_code=403, detail="Co tai lieu khong thuoc quyen truy cap.")
        return {"mode": "documents", "document_ids": document_ids}

    if mode == "topic":
        category = source_scope.get("category")
        topic = source_scope.get("topic")
        if not isinstance(category, str) or not category.strip():
            raise HTTPException(status_code=400, detail="Chua chon topic hoac danh muc.")
        query = db.query(Document).filter(
            Document.user_id == user_id,
            Document.status == "ready",
            Document.category == category.strip(),
        )
        normalized: Dict[str, Any] = {"mode": "topic", "category": category.strip()}
        if isinstance(topic, str) and topic.strip():
            normalized["topic"] = topic.strip()
            query = query.filter(Document.topic == topic.strip())
        if not query.first():
            raise HTTPException(status_code=400, detail="Nguon topic da chon chua co tai lieu san sang.")
        return normalized

    raise HTTPException(status_code=400, detail="Source scope khong hop le.")


_intent_router = IntentRouter()

def _classify_intent(text: str) -> str:
    """Classify user intent for chat routing."""
    result = _intent_router.classify(text)
    return result.intent


def _user_has_ready_documents(db: Session, user_id: str) -> bool:
    return any(doc.status == "ready" for doc in crud.get_user_documents(db, user_id))


def _coerce_response_text(response) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        parts = []
        for item in response:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(
                    item.get("text")
                    or item.get("content")
                    or json.dumps(item, ensure_ascii=False)
                )
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(response)


def _get_agent(intent: str, user_id: str):
    """Lazy-load the appropriate agent based on intent, with user_id for auth."""
    if intent == "calendar":
        from agents.calendar.agent import CalendarAgent
        return CalendarAgent(user_id=user_id)
    elif intent == "note":
        from agents.note.agent import NoteAgent
        return NoteAgent(user_id=user_id)
    elif intent == "email":
        from agents.email.agent import EmailAgent
        return EmailAgent(user_id=user_id)
    elif intent == "docsearch":
        from agents.doc_search.agent import DocSearchAgent
        return DocSearchAgent(user_id=user_id)
    elif intent == "teams":
        from agents.teams.agent import TeamsAgent
        return TeamsAgent(user_id=user_id)
    return None


async def _stream_chat(
    user_input: str,
    chat_id: str,
    user_id: str,
    db: Session,
    source_scope: Optional[Dict[str, Any]] = None,
):
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
        if intent == "unknown" and source_scope:
            intent = "docsearch"
        if intent == "unknown" and _user_has_ready_documents(db, user_id):
            intent = "docsearch"

        # Send agent event
        yield f"event: agent\ndata: {json.dumps({'agent': intent})}\n\n"

        # Get response from agent (pass user_id for Google API auth)
        agent = _get_agent(intent, user_id=user_id)
        if agent is None:
            response_text = "Xin lỗi, mình chưa hiểu rõ yêu cầu. Bạn có thể nói rõ hơn về Lịch học, Ghi chú, Email, Teams hoặc Tài liệu không?"
        elif intent == "docsearch":
            response_text = _coerce_response_text(agent.run(user_input, source_scope=source_scope))
        else:
            response_text = _coerce_response_text(agent.run(user_input))

        # Stream response token by token
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"event: token\ndata: {json.dumps({'content': chunk})}\n\n"

        # Save messages to DB
        source_scope_json = _source_scope_to_json(source_scope)
        crud.add_message(db, chat_id, "user", user_input, source_scope=source_scope_json)
        crud.add_message(db, chat_id, "assistant", response_text, agent=intent, source_scope=source_scope_json)

        # Auto-generate chat title from first message
        chat = crud.get_chat_by_id(db, chat_id)
        if chat and chat.title == "Cuộc trò chuyện mới":
            chat.title = user_input[:50] + ("..." if len(user_input) > 50 else "")
            db.commit()

        yield f"event: done\ndata: {json.dumps({'chat_id': chat_id, 'source_scope': source_scope}, ensure_ascii=False)}\n\n"

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

    if body.source_scope is not None:
        source_scope = _normalize_source_scope(db, current_user.id, body.source_scope)
        crud.update_chat_source_scope(db, chat_id, _source_scope_to_json(source_scope))
    else:
        source_scope = _parse_source_scope(chat.source_scope)

    return StreamingResponse(
        _stream_chat(body.message, chat_id, current_user.id, db, source_scope=source_scope),
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
            source_scope=_parse_source_scope(c.source_scope),
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
            source_scope=_parse_source_scope(m.source_scope),
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
