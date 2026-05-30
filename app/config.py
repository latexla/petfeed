from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULTS: dict[str, set[str]] = {
    "JWT_SECRET": {"change-me-in-production", "change_me", ""},
    "ADMIN_TOKEN": {"change_me", "change_me_in_production", ""},
    "DEEPSEEK_API_KEY": {"", "your_deepseek_key_here"},
    "TELEGRAM_BOT_TOKEN": {"", "your_bot_token_here"},
}


class Settings(BaseSettings):
    APP_ENV: Literal["development", "production"] = "development"

    DATABASE_URL: str

    @property
    def async_database_url(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)

    REDIS_URL: str
    TELEGRAM_BOT_TOKEN: str
    BACKEND_URL: str = "http://localhost:8000"
    ADMIN_TOKEN: str = "change_me"
    DEEPSEEK_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    AI_DAILY_LIMIT: int = 10

    MINIAPP_URL: str = ""
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: str = ""

    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    @model_validator(mode="after")
    def _enforce_production_secrets(self):
        if self.APP_ENV != "production":
            return self
        problems: list[str] = []
        for field, bad_values in INSECURE_DEFAULTS.items():
            if getattr(self, field) in bad_values:
                problems.append(f"{field} is unset or uses an insecure default value")
        if len(self.JWT_SECRET) < 32:
            problems.append("JWT_SECRET must be at least 32 characters in production")
        if not self.ALLOWED_ORIGINS.strip():
            problems.append("ALLOWED_ORIGINS must be a non-empty comma-separated list in production")
        if problems:
            joined = "\n  - ".join(problems)
            raise RuntimeError(
                f"Refusing to start in production with insecure config:\n  - {joined}"
            )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
