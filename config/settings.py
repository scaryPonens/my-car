"""
Application settings using Pydantic Settings.

Loads configuration from environment variables with type validation
and default values. Uses functional patterns for immutable configuration.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are immutable once loaded. Use get_settings()
    to access the singleton instance.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Configuration
    telegram_bot_token: str = Field(
        ...,
        description="Telegram Bot API token from @BotFather",
    )

    # Smartcar Configuration
    smartcar_client_id: str = Field(
        ...,
        description="Smartcar API client ID",
    )
    smartcar_client_secret: str = Field(
        ...,
        description="Smartcar API client secret",
    )
    smartcar_redirect_uri: str = Field(
        ...,
        description="OAuth redirect URI for Smartcar",
    )
    smartcar_mode: Literal["live", "simulated"] = Field(
        default="simulated",
        description="Smartcar API mode (live or simulated)",
    )

    # LLM Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for GPT models",
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude models",
    )
    default_llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="Default LLM provider to use",
    )

    # Supabase Configuration
    supabase_url: str = Field(
        ...,
        description="Supabase project URL",
    )
    supabase_key: str = Field(
        ...,
        description="Supabase anon/public key",
    )
    supabase_service_key: str = Field(
        default="",
        description="Supabase service role key for admin operations",
    )

    # Application Configuration
    environment: Literal["development", "production"] = Field(
        default="development",
        description="Application environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for session management",
    )
    port: int = Field(
        default=8000,
        description="Port for the FastAPI server",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host for the FastAPI server",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the application settings singleton.

    Uses lru_cache to ensure settings are only loaded once.
    This is a pure function that returns an immutable settings object.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()


# Convenience export for direct import
settings = get_settings()
