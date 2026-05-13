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
    ensure_schema()


def ensure_schema():
    """Apply small SQLite schema upgrades for local development."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    additions = {
        "microsoft_access_token": "TEXT",
        "microsoft_refresh_token": "TEXT",
        "microsoft_token_expires_at": "DATETIME",
        "microsoft_account_email": "VARCHAR",
    }

    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        existing = {row[1] for row in rows}
        for column, column_type in additions.items():
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {column_type}")
