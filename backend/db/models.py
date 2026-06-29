"""
Các ORM Model SQLAlchemy cho ứng dụng ORCA.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Float
)
from sqlalchemy.orm import relationship

from db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)  # URL avatar
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    microsoft_access_token = Column(Text, nullable=True)
    microsoft_refresh_token = Column(Text, nullable=True)
    microsoft_token_expires_at = Column(DateTime, nullable=True)
    microsoft_account_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    email_summaries = relationship("EmailSummary", back_populates="user", cascade="all, delete-orphan")
    email_preference = relationship("EmailPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="Cuộc trò chuyện mới")
    source_scope = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=_uuid)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    agent = Column(String, nullable=True)  # "calendar" | "note" | "email" | "docsearch" | null
    source_scope = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    chat = relationship("Chat", back_populates="messages")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # "pdf" | "docx" | "pptx" | "txt"
    file_size = Column(Integer, nullable=False)  # bytes
    content_hash = Column(String, nullable=True, index=True)  # sha256 của content
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="processing")  # "processing" | "ready" | "error"
    error_message = Column(Text, nullable=True)
    
    # Phân loại chủ đề
    topic = Column(String, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(Text, nullable=True)          # JSON array string: '["đại số", "ma trận"]'
    
    # Nguồn cloud (Drive/OneDrive)
    source_type = Column(String, default="manual_upload") # "manual_upload" | "google_drive" | "onedrive"
    drive_file_id = Column(String, nullable=True)
    drive_modified_time = Column(String, nullable=True)
    drive_mime_type = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="documents")


class EmailSummary(Base):
    __tablename__ = "email_summaries"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    gmail_id = Column(String, unique=True, nullable=False, index=True)
    subject = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    sender_email = Column(String, nullable=True)
    received_at = Column(DateTime, nullable=True)
    scan_session = Column(String, nullable=True)      # "morning", "noon", "afternoon", "evening"
    summary = Column(Text, nullable=True)
    priority = Column(String, nullable=True)          # "urgent", "important", "follow_up", "info"
    deadline = Column(DateTime, nullable=True)
    calendar_event_id = Column(String, nullable=True)
    requires_reply = Column(Boolean, default=False)
    action_items = Column(Text, nullable=True)        # JSON array string
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="email_summaries")


class EmailPreference(Base):
    __tablename__ = "email_preferences"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    academic_domains = Column(Text, default='[]')      # JSON array string
    auto_create_calendar = Column(Boolean, default=True)
    notify_urgent_toast = Column(Boolean, default=True)
    notify_all_toast = Column(Boolean, default=False)
    last_scan_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="email_preference")
