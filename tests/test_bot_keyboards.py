from unittest.mock import AsyncMock, patch
import pytest
from aiogram.types import BotCommand


@pytest.mark.asyncio
async def test_set_my_commands_registers_start_and_help():
    mock_bot = AsyncMock()
    mock_bot.set_my_commands = AsyncMock()

    commands = [
        BotCommand(command="start", description="Создать профиль питомца или вернуться в меню"),
        BotCommand(command="help",  description="Что умеет бот и как им пользоваться"),
    ]
    await mock_bot.set_my_commands(commands)

    mock_bot.set_my_commands.assert_called_once()
    call_args = mock_bot.set_my_commands.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].command == "start"
    assert call_args[1].command == "help"
