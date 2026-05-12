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
    gemini_api_key: str = ""
    # gemini-2.0-flash: nhanh + miễn phí bậc cao; gemini-1.5-pro: chất lượng cao hơn
    gemini_model: str = "gemini-2.5-flash"

    # ── OpenAI ─────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Microsoft Azure / Graph ────────────────────────────────────────────
    azure_client_id: str = Field(default="", validation_alias=AliasChoices("AZURE_CLIENT_ID", "MS_CLIENT_ID"))
    azure_client_secret: str = Field(default="", validation_alias=AliasChoices("AZURE_CLIENT_SECRET", "MS_CLIENT_SECRET"))
    azure_tenant_id: str = Field(default="", validation_alias=AliasChoices("AZURE_TENANT_ID", "MS_TENANT_ID"))
    # Delegated user UPN or object-id (needed for application-level access)
    graph_user_id: str = Field(default="me", validation_alias=AliasChoices("GRAPH_USER_ID", "MS_GRAPH_USER_ID"))

    # ── Google OAuth2 Web Flow ─────────────────────────────────────────────
    # Client ID và Secret dùng cho server-side authorization code exchange
    google_client_id: str = ""       # Lấy từ Google Cloud Console (Web app)
    google_client_secret: str = ""   # Lấy từ Google Cloud Console
    google_redirect_uri: str = "http://localhost:3000"  # Phải khớp với Google Console
    google_calendar_id: str = "primary"

    # ── Google Drive RAG Integration ────────────────────────────────────────
    # Số file tối đa được sync từ Drive vào RAG (tránh quá tải tài nguyên)
    google_drive_max_files: int = 50
    # Yêu cầu scope drive.readonly khi login (true = thêm scope Drive)
    google_drive_enabled: bool = True

    # ── Token Encryption ────────────────────────────────────────────────────
    # Sinh key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    token_encryption_key: str = ""

    # ── JWT Authentication ──────────────────────────────────────────────
    jwt_secret_key: str = "orca_super_secret_jwt_key_change_in_production"
    jwt_algorithm: str = "HS256"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "sqlite:///./orca.db"

    # ── App ────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    mock_graph: bool = True  # Use mock Graph service when True (dev/test)
    # calendar_provider: "mock" | "google" | "msgraph"
    calendar_provider: str = "google"
    email_provider: str = "google"
    email_providers: str = ""
    default_email_provider: str = "gmail"
    note_provider: str = "google"  # "sqlite" for local storage, "google" for Google Keep
    teams_provider: str = "msgraph"




# Singleton – import this everywhere
settings = Settings()
