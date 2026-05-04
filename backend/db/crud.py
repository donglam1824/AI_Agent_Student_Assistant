"""
db/crud.py
----------
Database CRUD operations for ORCA models.
"""

from typing import Optional
from sqlalchemy.orm import Session

from db.models import User, Chat, ChatMessage, Document, Note, EmailSummary, EmailPreference


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
    from core.crypto import encrypt_token
    user = get_user_by_email(db, email)
    if user:
        if name:
            user.name = name
        if picture:
            user.picture = picture
        if google_access_token:
            user.google_access_token = encrypt_token(google_access_token)
        if google_refresh_token:
            user.google_refresh_token = encrypt_token(google_refresh_token)
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        name=name,
        picture=picture,
        google_access_token=encrypt_token(google_access_token),
        google_refresh_token=encrypt_token(google_refresh_token),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_tokens(
    db: Session,
    user_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> Optional[User]:
    """
    Cập nhật Google tokens đã mã hóa vào DB.
    Chỉ cập nhật refresh_token nếu được cung cấp (Google không luôn trả về mới).
    """
    from core.crypto import encrypt_token
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.google_access_token = encrypt_token(access_token)
    if refresh_token:
        user.google_refresh_token = encrypt_token(refresh_token)
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


# ── EmailSummary ─────────────────────────────────────────────────────────

def create_email_summary(db: Session, user_id: str, gmail_id: str, **kwargs) -> EmailSummary:
    summary = EmailSummary(user_id=user_id, gmail_id=gmail_id, **kwargs)
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def get_email_summaries(db: Session, user_id: str, limit: int = 50) -> list[EmailSummary]:
    return (
        db.query(EmailSummary)
        .filter(EmailSummary.user_id == user_id)
        .order_by(EmailSummary.received_at.desc())
        .limit(limit)
        .all()
    )


def get_email_summary_by_gmail_id(db: Session, gmail_id: str) -> Optional[EmailSummary]:
    return db.query(EmailSummary).filter(EmailSummary.gmail_id == gmail_id).first()


def mark_email_read(db: Session, summary_id: str) -> Optional[EmailSummary]:
    summary = db.query(EmailSummary).filter(EmailSummary.id == summary_id).first()
    if summary:
        summary.is_read = True
        db.commit()
        db.refresh(summary)
    return summary


def update_email_summary_calendar_event(db: Session, summary_id: str, event_id: str) -> Optional[EmailSummary]:
    summary = db.query(EmailSummary).filter(EmailSummary.id == summary_id).first()
    if summary:
        summary.calendar_event_id = event_id
        db.commit()
        db.refresh(summary)
    return summary


# ── EmailPreference ──────────────────────────────────────────────────────

def get_email_preference(db: Session, user_id: str) -> Optional[EmailPreference]:
    pref = db.query(EmailPreference).filter(EmailPreference.user_id == user_id).first()
    if not pref:
        # Create default preference if not exists
        pref = EmailPreference(user_id=user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


def update_email_preference(db: Session, user_id: str, **kwargs) -> Optional[EmailPreference]:
    pref = get_email_preference(db, user_id)
    if pref:
        for key, value in kwargs.items():
            if hasattr(pref, key):
                setattr(pref, key, value)
        db.commit()
        db.refresh(pref)
    return pref


