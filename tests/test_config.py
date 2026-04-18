from app.config import settings


def test_settings_loaded():
    assert settings.DATABASE_URL is not None
    assert settings.REDIS_URL is not None
    assert settings.TELEGRAM_BOT_TOKEN is not None
