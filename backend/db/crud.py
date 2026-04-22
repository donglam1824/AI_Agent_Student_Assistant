"""
db/crud.py
----------
Database CRUD operations for ORCA models.
"""

from typing import Optional
from sqlalchemy.orm import Session

from db.models import User, Chat, ChatMessage, Document, Note


# ── User ──────────────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_or_update_user(
    db: Session,
    email: str,
    name: str = None,
    picture: str = None,
    google_access_token: str = None,
    google_refresh_token: str = None,
) -> User:
    user = get_user_by_email(db, email)
    if user:
        if name:
            user.name = name
        if picture:
            user.picture = picture
        if google_access_token:
            user.google_access_token = google_access_token
        if google_refresh_token:
            user.google_refresh_token = google_refresh_token
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        name=name,
        picture=picture,
        google_access_token=google_access_token,
        google_refresh_token=google_refresh_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Chat ──────────────────────────────────────────────────────────────────

def create_chat(db: Session, user_id: str, title: str = "Cuộc trò chuyện mới") -> Chat:
    chat = Chat(user_id=user_id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def get_user_chats(db: Session, user_id: str, limit: int = 50) -> list[Chat]:
    return (
        db.query(Chat)
        .filter(Chat.user_id == user_id)
        .order_by(Chat.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_chat_by_id(db: Session, chat_id: str) -> Optional[Chat]:
    return db.query(Chat).filter(Chat.id == chat_id).first()


def delete_chat(db: Session, chat_id: str) -> bool:
    chat = get_chat_by_id(db, chat_id)
    if chat:
        db.delete(chat)
        db.commit()
        return True
    return False


# ── ChatMessage ───────────────────────────────────────────────────────────

def add_message(
    db: Session,
    chat_id: str,
    role: str,
    content: str,
    agent: str = None,
) -> ChatMessage:
    msg = ChatMessage(chat_id=chat_id, role=role, content=content, agent=agent)
    db.add(msg)
    # Update the chat's updated_at timestamp
    chat = get_chat_by_id(db, chat_id)
    if chat:
        from datetime import datetime, timezone
        chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


def get_chat_messages(db: Session, chat_id: str) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at)
        .all()
    )


# ── Document ─────────────────────────────────────────────────────────────

def create_document(
    db: Session,
    user_id: str,
    filename: str,
    file_type: str,
    file_size: int,
) -> Document:
    doc = Document(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_document_status(
    db: Session,
    doc_id: str,
    status: str,
    chunk_count: int = None,
    error_message: str = None,
) -> Optional[Document]:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        doc.status = status
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        if error_message is not None:
            doc.error_message = error_message
        db.commit()
        db.refresh(doc)
    return doc


def get_user_documents(db: Session, user_id: str) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def delete_document(db: Session, doc_id: str) -> bool:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        db.delete(doc)
        db.commit()
        return True
    return False


# ── Note (SQLite local storage) ──────────────────────────────────────────

def create_note(db: Session, user_id: str, title: str, content: str = "") -> Note:
    note = Note(user_id=user_id, title=title, content=content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_user_notes(db: Session, user_id: str, limit: int = 20) -> list[Note]:
    return (
        db.query(Note)
        .filter(Note.user_id == user_id)
        .order_by(Note.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_note_by_id(db: Session, note_id: str) -> Optional[Note]:
    return db.query(Note).filter(Note.id == note_id).first()


def update_note(
    db: Session,
    note_id: str,
    title: str = None,
    content: str = None,
) -> Optional[Note]:
    note = get_note_by_id(db, note_id)
    if note:
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        db.commit()
        db.refresh(note)
    return note


def delete_note(db: Session, note_id: str) -> bool:
    note = get_note_by_id(db, note_id)
    if note:
        db.delete(note)
        db.commit()
        return True
    return False

