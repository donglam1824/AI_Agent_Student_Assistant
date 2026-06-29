"""
config/settings.py
------------------
Centralized configuration using pydantic-settings.
All values are loaded from environment variables / .env file.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ───────────────────────────────────────────────────────
    # Chọn provider mặc định: "gemini" | "openai" | "ollama"
    default_llm_provider: str = "gemini"

    # ── Google Gemini ──────────────────────────────────────────────────────
    gemini_model: str = "gemini-1.5-flash"
    gemini_api_key: str = ""
    # Model Gemini dự phòng khi lỗi quota. Ưu tiên model RPD cao hơn lên trước.
    gemini_fallback_models: str = (
        "gemini-3.1-flash-lite,"
        "gemini-2.5-flash-lite,"
        "gemini-3-flash,"
        "gemini-3.5-flash"
    )
    llm_fallback_cooldown_seconds: int = 60

    # ── OpenAI ─────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # "local" để chạy sentence-transformers cục bộ tránh tốn API quota. Hỗ trợ: "gemini", "openai".
    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = 32

    # ── Microsoft Azure / Graph ────────────────────────────────────────────
    azure_client_id: str = Field(default="", validation_alias=AliasChoices("AZURE_CLIENT_ID", "MS_CLIENT_ID"))
    azure_client_secret: str = Field(default="", validation_alias=AliasChoices("AZURE_CLIENT_SECRET", "MS_CLIENT_SECRET"))
    azure_tenant_id: str = Field(default="", validation_alias=AliasChoices("AZURE_TENANT_ID", "MS_TENANT_ID"))
    # UPN hoặc object-id của user (cần cho quyền ứng dụng)
    graph_user_id: str = Field(default="me", validation_alias=AliasChoices("GRAPH_USER_ID", "MS_GRAPH_USER_ID"))
    microsoft_redirect_uri: str = Field(default="http://localhost:3000/auth/microsoft/callback", validation_alias=AliasChoices("MICROSOFT_REDIRECT_URI", "MS_REDIRECT_URI"))
    microsoft_scopes: str = (
        "openid profile email offline_access User.Read "
        "Mail.Read Mail.Send Team.ReadBasic.All Channel.ReadBasic.All "
        "ChannelMessage.Read.All EduRoster.ReadBasic EduAssignments.ReadBasic "
        "Files.Read"
    )

    # Client ID & Secret cho OAuth flow
    google_client_id: str = ""       # Google Cloud Console (Web app)
    google_client_secret: str = ""   
    google_redirect_uri: str = "http://localhost:3000"  # Trùng redirect URI trong Google Console
    google_calendar_id: str = "primary"

    # Giới hạn số file sync từ Drive tránh quá tải
    google_drive_max_files: int = 50
    # Thêm scope drive.readonly khi login
    google_drive_enabled: bool = True

    # Fernet key để encrypt tokens
    token_encryption_key: str = ""

    # ── JWT Authentication ──────────────────────────────────────────────
    jwt_secret_key: str = "orca_super_secret_jwt_key_change_in_production"
    jwt_algorithm: str = "HS256"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "sqlite:///./orca.db"

    # ── App ────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    mock_graph: bool = True  # Mock Graph khi dev/test
    # calendar_provider: "mock" | "google" | "msgraph"
    calendar_provider: str = "google"
    email_provider: str = "google"
    email_providers: str = ""
    default_email_provider: str = "gmail"
    note_provider: str = "google"  # "sqlite" (local) hoặc "google" (Google Keep)
    teams_provider: str = "msgraph"




# Singleton dùng chung toàn app
settings = Settings()
