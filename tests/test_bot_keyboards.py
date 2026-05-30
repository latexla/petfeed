from unittest.mock import AsyncMock

import pytest
from aiogram.types import BotCommand, ReplyKeyboardMarkup

from app.config import settings
from bot.keyboards import miniapp_keyboard
from bot.main import BOT_COMMANDS


@pytest.mark.asyncio
async def test_set_my_commands_registers_start_and_help():
    mock_bot = AsyncMock()
    mock_bot.set_my_commands = AsyncMock()

    await mock_bot.set_my_commands(BOT_COMMANDS)

    mock_bot.set_my_commands.assert_called_once()
    call_args = mock_bot.set_my_commands.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].command == "start"
    assert call_args[1].command == "help"


def test_miniapp_keyboard_returns_persistent_webapp_button(monkeypatch):
    monkeypatch.setattr(settings, "MINIAPP_URL", "https://example.com/app")
    kb = miniapp_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)
    assert kb.is_persistent is True
    assert kb.resize_keyboard is True
    button = kb.keyboard[0][0]
    assert button.text == "🌐 Открыть приложение"
    assert button.web_app is not None
    assert button.web_app.url == "https://example.com/app"


def test_miniapp_keyboard_returns_none_when_no_url(monkeypatch):
    monkeypatch.setattr(settings, "MINIAPP_URL", "")
    result = miniapp_keyboard()
    assert result is None
