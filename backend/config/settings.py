"""
config/settings.py
------------------
Centralized configuration using pydantic-settings.
All values are loaded from environment variables / .env file.
"""

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
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = ""
    # Delegated user UPN or object-id (needed for application-level access)
    graph_user_id: str = "me"

    # ── Google OAuth2 Web Flow ─────────────────────────────────────────────
    # Client ID và Secret dùng cho server-side authorization code exchange
    google_client_id: str = ""       # Lấy từ Google Cloud Console (Web app)
    google_client_secret: str = ""   # Lấy từ Google Cloud Console
    google_redirect_uri: str = "http://localhost:3000"  # Phải khớp với Google Console
    google_calendar_id: str = "primary"

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
    note_provider: str = "google"  # "sqlite" for local storage, "google" for Google Keep




# Singleton – import this everywhere
settings = Settings()
