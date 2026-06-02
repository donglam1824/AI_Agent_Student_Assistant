"""
db/database.py
--------------
SQLAlchemy engine, session, and base model configuration.
Uses SQLite for local development (no external DB server needed).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./orca.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """FastAPI dependency – yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (call once at startup)."""
    Base.metadata.create_all(bind=engine)
    # Enable WAL mode for SQLite to prevent locking issues
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
    ensure_schema()


def ensure_schema():
    """Apply small SQLite schema upgrades for local development."""
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

    with engine.begin() as conn:
        # Migrate users table
        rows_users = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        existing_users = {row[1] for row in rows_users}
        for column, column_type in additions_users.items():
            if column not in existing_users:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {column_type}")

        # Migrate documents table
        rows_docs = conn.exec_driver_sql("PRAGMA table_info(documents)").fetchall()
        existing_docs = {row[1] for row in rows_docs}
        for column, column_type in additions_documents.items():
            if column not in existing_docs:
                conn.exec_driver_sql(f"ALTER TABLE documents ADD COLUMN {column} {column_type}")
