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

    # ── OpenAI ─────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Microsoft Azure / Graph ────────────────────────────────────────────
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = ""
    # Delegated user UPN or object-id (needed for application-level access)
    graph_user_id: str = "me"

    # ── App ────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    mock_graph: bool = True  # Use mock Graph service when True (dev/test)


# Singleton – import this everywhere
settings = Settings()
