"""All settings come from environment variables (or the .env file). Nothing is hard-coded."""
from functools import lru_cache
from decimal import Decimal
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    app_name: str = "CartPilot AI"
    database_url: str = "sqlite:///./cartpilot.db"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = ""  # optional backup model if the main one is overloaded

    product_provider: str = "channel3"
    channel3_api_key: str = ""
    channel3_base_url: str = "https://api.trychannel3.com"
    product_currency: str = "USD"
    inr_per_usd: Optional[Decimal] = None

    paypal_env: str = "sandbox"
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_webhook_id: str = ""
    paypal_currency: str = "USD"

    encryption_key: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def paypal_base_url(self) -> str:
        return "https://api-m.paypal.com" if self.paypal_env == "live" else "https://api-m.sandbox.paypal.com"

    def require_jwt_secret(self) -> str:
        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET is empty. Copy .env.example to .env and set JWT_SECRET.")
        return self.jwt_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()