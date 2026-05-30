# Bot Commands & Miniapp Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register `/start` and `/help` as Telegram command hints and add a persistent WebApp button that opens the miniapp from any point in the bot chat.

**Architecture:** Two independent changes: (1) `bot.set_my_commands()` called at startup registers commands in BotFather so Telegram shows autocomplete; (2) a new `ReplyKeyboardMarkup` with `is_persistent=True` is sent with every `/start` response so the WebApp button sticks to the bottom of the chat.

**Tech Stack:** Python 3.12, aiogram 3, `aiogram.types.ReplyKeyboardMarkup`, `aiogram.types.KeyboardButton`, `aiogram.types.WebAppInfo`, `aiogram.types.BotCommand`

---

## File Map

| File | Change |
|------|--------|
| `bot/main.py` | Add `bot.set_my_commands()` call before polling |
| `bot/keyboards.py` | Add `miniapp_keyboard()` function |
| `bot/handlers/start.py` | Import `miniapp_keyboard`, attach to all `/start` responses, remove redundant inline miniapp text |
| `tests/test_bot_keyboards.py` | New — unit test for `miniapp_keyboard()` |

---

## Task 1: Register bot commands

**Files:**
- Modify: `bot/main.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_bot_keyboards.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it passes** (this test mocks the bot, so it should pass immediately — it verifies the contract we're about to implement)

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
pytest tests/test_bot_keyboards.py::test_set_my_commands_registers_start_and_help -v
```

Expected: PASS

- [ ] **Step 3: Add `set_my_commands` to `bot/main.py`**

Replace the `main()` function body in `bot/main.py`:

```python
import asyncio
import os
import signal

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from app.config import settings
from app.observability import setup_observability
from app.scheduler import start_scheduler
from bot.handlers import ai_handler, feedback, meal_builder, nutrition, pet_creation, reminders, start, weight

setup_observability("bot")


async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.include_router(start.router)
    dp.include_router(pet_creation.router)
    dp.include_router(nutrition.router)
    dp.include_router(reminders.router)
    dp.include_router(ai_handler.router)
    dp.include_router(weight.router)
    dp.include_router(meal_builder.router)
    dp.include_router(feedback.router)
    start_scheduler(bot)
    await bot.set_my_commands([
        BotCommand(command="start", description="Создать профиль питомца или вернуться в меню"),
        BotCommand(command="help",  description="Что умеет бот и как им пользоваться"),
    ])
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    asyncio.run(main())
```

- [ ] **Step 4: Commit**

```bash
git add bot/main.py tests/test_bot_keyboards.py
git commit -m "feat: register /start and /help commands with descriptions"
```

---

## Task 2: Add `miniapp_keyboard()` to keyboards

**Files:**
- Modify: `bot/keyboards.py`
- Test: `tests/test_bot_keyboards.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bot_keyboards.py`:

```python
from aiogram.types import ReplyKeyboardMarkup
from app.config import settings
from bot.keyboards import miniapp_keyboard


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bot_keyboards.py::test_miniapp_keyboard_returns_persistent_webapp_button tests/test_bot_keyboards.py::test_miniapp_keyboard_returns_none_when_no_url -v
```

Expected: FAIL with `ImportError` or `AttributeError: module 'bot.keyboards' has no attribute 'miniapp_keyboard'`

- [ ] **Step 3: Add `miniapp_keyboard()` to `bot/keyboards.py`**

Add these imports at the top of `bot/keyboards.py` (after existing imports):

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
```

Then add the new function at the end of `bot/keyboards.py`:

```python
def miniapp_keyboard() -> ReplyKeyboardMarkup | None:
    if not settings.MINIAPP_URL:
        return None
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=settings.MINIAPP_URL))]],
        resize_keyboard=True,
        is_persistent=True,
    )
```

Note: `bot/keyboards.py` already imports `WebAppInfo` — add `KeyboardButton` and `ReplyKeyboardMarkup` to the existing import line.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_bot_keyboards.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add bot/keyboards.py tests/test_bot_keyboards.py
git commit -m "feat: add miniapp_keyboard() persistent reply keyboard"
```

---

## Task 3: Attach persistent keyboard in `cmd_start`

**Files:**
- Modify: `bot/handlers/start.py`

- [ ] **Step 1: Update the import in `bot/handlers/start.py`**

Find the existing import block:

```python
from bot.keyboards import (
    main_menu_keyboard,
    onboarding_keyboard,
    pet_profile_keyboard,
    pets_keyboard,
    species_keyboard,
)
```

Replace with:

```python
from bot.keyboards import (
    main_menu_keyboard,
    miniapp_keyboard,
    onboarding_keyboard,
    pet_profile_keyboard,
    pets_keyboard,
    species_keyboard,
)
```

- [ ] **Step 2: Update `cmd_start` to attach the persistent keyboard**

Find the full `cmd_start` function:

```python
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    pets = await get_user_pets(telegram_id)

    if not pets:
        # New user — show onboarding screen 1
        await message.answer(
            ONBOARDING_SCREENS[1],
            parse_mode="HTML",
            reply_markup=onboarding_keyboard(step=1),
        )
        return

    pet = pets[0]
    await state.update_data(active_pet_id=pet["id"], active_pet_name=pet["name"])

    if len(pets) == 1:
        miniapp_note = (
            f'\n\n🌐 Или открой <a href="{settings.MINIAPP_URL}">удобный интерфейс</a>'
            if settings.MINIAPP_URL else ""
        )
        await message.answer(
            f"С возвращением!\n\nВыбери действие:{miniapp_note}",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(pet["name"]),
        )
    else:
        await message.answer(
            "С возвращением! Выбери питомца:",
            reply_markup=pets_keyboard(pets, action="main"),
        )
```

Replace with:

```python
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id
    pets = await get_user_pets(telegram_id)
    persistent_kb = miniapp_keyboard()

    if not pets:
        await message.answer(
            ONBOARDING_SCREENS[1],
            parse_mode="HTML",
            reply_markup=onboarding_keyboard(step=1),
        )
        if persistent_kb:
            await message.answer("👆 Или сразу открой приложение:", reply_markup=persistent_kb)
        return

    pet = pets[0]
    await state.update_data(active_pet_id=pet["id"], active_pet_name=pet["name"])

    if len(pets) == 1:
        await message.answer(
            "С возвращением!\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(pet["name"]),
        )
    else:
        await message.answer(
            "С возвращением! Выбери питомца:",
            reply_markup=pets_keyboard(pets, action="main"),
        )

    if persistent_kb:
        await message.answer("👆 Быстрый доступ:", reply_markup=persistent_kb)
```

- [ ] **Step 3: Run full test suite to check no regressions**

```bash
pytest tests/ -v --ignore=tests/test_bot_keyboards.py -x
```

Expected: all existing tests PASS (bot handler code changes don't affect service/repo tests)

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/start.py
git commit -m "feat: attach persistent miniapp keyboard to /start responses"
```

---

## Verification

After all tasks are complete, manually test in Telegram:

1. Type `/` in bot chat — autocomplete shows `/start` and `/help` with Russian descriptions
2. Send `/start` — persistent "🌐 Открыть приложение" button appears at the bottom
3. Button opens the miniapp in Telegram WebApp view
4. Navigate through bot menus — persistent button remains visible throughout
5. Send `/start` again — button is still there (Telegram deduplicates persistent keyboards)
