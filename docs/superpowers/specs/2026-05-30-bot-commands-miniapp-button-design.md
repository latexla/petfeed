# Bot Commands & Miniapp Button — Design Spec
_Date: 2026-05-30_

## Scope

Two small improvements to the Telegram bot:
1. Register `/start` and `/help` with descriptions so Telegram shows autocomplete hints when users type `/`
2. Add a persistent Reply Keyboard button that opens the miniapp, always visible at the bottom of the chat

---

## 1. Command Registration

**Problem:** Bot commands are not registered with BotFather programmatically. Users who type `/` see no suggestions.

**Change:** Call `await bot.set_my_commands(...)` in `bot/main.py` during startup, before polling begins.

**Commands to register:**

| Command | Description |
|---------|-------------|
| `/start` | Создать профиль питомца или вернуться в меню |
| `/help` | Что умеет бот и как им пользоваться |

**Files:** `bot/main.py`

---

## 2. Persistent Miniapp Button

**Problem:** The miniapp button in the main menu inline keyboard is only reachable after navigating through the bot menu. Users have no always-visible shortcut to the miniapp.

**Change:** Show a persistent `ReplyKeyboardMarkup` alongside the existing messages in `cmd_start`. The keyboard contains a single WebApp button. It sticks to the bottom of the chat and does not interfere with inline keyboards or FSM states.

**Keyboard spec:**
```
ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=MINIAPP_URL))]],
    resize_keyboard=True,
    is_persistent=True,
)
```

**Behaviour:**
- Shown only when `settings.MINIAPP_URL` is set (non-empty). If unset, `reply_markup` is omitted — no crash.
- Sent as `reply_markup` in the `/start` response (both first-time onboarding message and returning-user menu message).
- For the multi-pet case (pet selection screen), also attach the keyboard so the button appears immediately.

**Files:** `bot/keyboards.py` (new `miniapp_keyboard()` function), `bot/handlers/start.py` (`cmd_start`)

---

## Implementation Order

1. Register commands in `bot/main.py` — one-liner, zero risk
2. Add `miniapp_keyboard()` to `bot/keyboards.py`
3. Attach keyboard in `cmd_start` handler in `bot/handlers/start.py`

---

## Out of Scope

- Adding new slash commands (e.g. `/nutrition`, `/reminders`) — not needed, functionality is menu-driven
- Hiding the persistent keyboard during FSM flows — Telegram handles coexistence of reply and inline keyboards natively
