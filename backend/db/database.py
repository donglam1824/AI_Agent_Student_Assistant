"""
Cấu hình kết nối DB (SQLite) qua SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./orca.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class cho các ORM models"""
    pass


def get_db():
    """Dependency lấy DB session cho mỗi request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Khởi tạo các bảng DB (gọi khi startup)"""
    Base.metadata.create_all(bind=engine)
    # Bật chế độ WAL cho SQLite để tránh bị khóa DB
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
    ensure_schema()


def ensure_schema():
    """Tự động migrate schema SQLite khi dev local"""
    if not DATABASE_URL.startswith("sqlite"):
        return

    additions_users = {
        "microsoft_access_token": "TEXT",
        "microsoft_refresh_token": "TEXT",
        "microsoft_token_expires_at": "DATETIME",
        "microsoft_account_email": "VARCHAR",
    }

    additions_documents = {
        "topic": "TEXT",
        "category": "TEXT",
        "tags": "TEXT",
        "content_hash": "TEXT",
        "source_type": "TEXT DEFAULT 'manual_upload'",
        "drive_file_id": "TEXT",
        "drive_modified_time": "TEXT",
        "drive_mime_type": "TEXT",
    }

    additions_chats = {
        "source_scope": "TEXT",
    }

    additions_chat_messages = {
        "source_scope": "TEXT",
    }

    with engine.begin() as conn:
        rows_users = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        existing_users = {row[1] for row in rows_users}
        for column, column_type in additions_users.items():
            if column not in existing_users:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {column_type}")

        rows_docs = conn.exec_driver_sql("PRAGMA table_info(documents)").fetchall()
        existing_docs = {row[1] for row in rows_docs}
        for column, column_type in additions_documents.items():
            if column not in existing_docs:
                conn.exec_driver_sql(f"ALTER TABLE documents ADD COLUMN {column} {column_type}")

        rows_chats = conn.exec_driver_sql("PRAGMA table_info(chats)").fetchall()
        existing_chats = {row[1] for row in rows_chats}
        for column, column_type in additions_chats.items():
            if column not in existing_chats:
                conn.exec_driver_sql(f"ALTER TABLE chats ADD COLUMN {column} {column_type}")

        rows_messages = conn.exec_driver_sql("PRAGMA table_info(chat_messages)").fetchall()
        existing_messages = {row[1] for row in rows_messages}
        for column, column_type in additions_chat_messages.items():
            if column not in existing_messages:
                conn.exec_driver_sql(f"ALTER TABLE chat_messages ADD COLUMN {column} {column_type}")
