from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
