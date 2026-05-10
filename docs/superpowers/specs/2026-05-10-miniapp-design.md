# Telegram Mini App — Design Spec

**Date:** 2026-05-10  
**Status:** Approved  
**Feature flag:** none (parallel channel, always available)

---

## Goal

Provide a rich web-based UI alongside the existing Telegram bot. Users choose their preferred interaction mode — both channels are fully functional. The onboarding flow informs users about both options at the end of pet creation.

---

## Architecture

```
Telegram Client
  │  window.Telegram.WebApp.initData
  ▼
miniapp/ (React + TypeScript + Vite)     ← Railway static service
  │  POST /v1/auth/miniapp { initData }
  ▼
FastAPI Backend                          ← existing Railway service
  │  HMAC-SHA256 verify (bot token server-side only)
  │  → JWT (15 min, JS memory only)
  │  → refresh token (7 days, httpOnly cookie)
  │
  │  GET /v1/pets, /v1/nutrition, /v1/reminders, /v1/ai, /v1/feedback
  │  Authorization: Bearer <jwt>
  ▼
PostgreSQL + Redis                       ← existing
```

---

## Security Model

| Rule | Implementation |
|---|---|
| `BOT_TOKEN` never reaches browser | Stays in FastAPI env only |
| `initData` not stored | Verified once, discarded |
| JWT in JS memory only | Never `localStorage` / `sessionStorage` — XSS proof |
| Refresh token inaccessible to JS | `httpOnly; Secure; SameSite=Strict` cookie |
| CORS restricted | Allowed origins: `*.railway.app`, `*.t.me` only |
| initData replay prevention | Telegram TTL 24h; backend rejects `auth_date` older than 1h |
| Internal bot→API auth unchanged | `X-Telegram-Id` header accepted only from Railway internal network |

---

## Auth Flow

```
1. Mini App opens → Telegram injects initData into window.Telegram.WebApp
2. AuthProvider → POST /v1/auth/miniapp { initData }
3. Backend:
   a. Parse initData fields
   b. Verify HMAC-SHA256 with BOT_TOKEN
   c. Check auth_date < 1 hour ago
   d. get_or_create user by telegram_id
   e. Return: { access_token, expires_in: 900 }
      Set-Cookie: refresh_token=<uuid>; HttpOnly; Secure; SameSite=Strict; Max-Age=604800
4. Frontend stores JWT in React context (memory only)
5. All API requests: Authorization: Bearer <jwt>
6. At 60s before expiry: silent POST /v1/auth/refresh → new JWT
7. On logout or app close: POST /v1/auth/logout → clear cookie
```

---

## Auth Middleware (modified)

`app/middleware/auth.py` — accept either channel:

```python
# Bot: X-Telegram-Id (trusted, internal Railway network)
# Mini App: Authorization: Bearer <jwt>
```

Both paths resolve to `request.state.telegram_id`. No existing endpoints change.

---

## New Backend Files

### `app/routers/auth.py`

| Endpoint | Method | Description |
|---|---|---|
| `/v1/auth/miniapp` | POST | Verify initData, return JWT + set refresh cookie |
| `/v1/auth/refresh` | POST | Validate refresh cookie, return new JWT |
| `/v1/auth/logout` | POST | Clear refresh cookie |

### `app/services/auth_service.py`

| Function | Description |
|---|---|
| `verify_initdata(initData, bot_token)` | HMAC-SHA256 check per Telegram spec |
| `create_jwt(telegram_id)` | Sign JWT, exp=15min |
| `verify_jwt(token)` | Decode + validate, raise 401 on failure |
| `create_refresh_token(telegram_id, redis)` | UUID stored in Redis TTL 7d |

---

## Frontend Structure

```
miniapp/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── src/
    ├── main.tsx
    ├── App.tsx              — router + AuthProvider + ThemeProvider
    ├── api/
    │   ├── client.ts        — axios instance, JWT injection, 401 → refresh
    │   ├── auth.ts          — miniapp auth, refresh, logout
    │   ├── pets.ts
    │   ├── nutrition.ts
    │   ├── reminders.ts
    │   ├── ai.ts
    │   └── feedback.ts
    ├── components/
    │   ├── TabBar.tsx
    │   ├── PetCard.tsx
    │   ├── NutritionCard.tsx
    │   ├── ReminderItem.tsx
    │   └── Toast.tsx
    ├── pages/
    │   ├── Home.tsx
    │   ├── Nutrition.tsx
    │   ├── Reminders.tsx
    │   ├── Profile.tsx
    │   └── AI.tsx
    └── hooks/
        ├── useAuth.ts
        ├── usePet.ts
        ├── useNutrition.ts
        └── useReminders.ts
```

---

## Screens

### Bottom Tab Bar (persistent)
```
[🏠 Главная] [🍽 Рацион] [⏰ Напоминания] [👤 Профиль]
```

### Home (`/`)
- Pet card: name, species, breed, weight, age
- Today's ration summary (kcal target, macros breakdown)
- Button "AI-ассистент →" → `/ai`

### Nutrition (`/nutrition`)
- Macros breakdown: protein / fat / carbs (g and %)
- Daily kcal target
- Collapsible stop-list section

### Reminders (`/reminders`)
- List of active reminders with time
- Add reminder (time picker)
- Delete reminder (swipe or button)

### Profile (`/profile`)
- User telegram info (name, username)
- Active pet details + "Изменить в боте →" deep link (edit stays in bot FSM)
- Multi-pet switcher (if multiple pets)
- "Оставить отзыв" button (hidden if already submitted)

### AI Assistant (`/ai`, no tab)
- Chat interface with message history (session only, not persisted)
- Daily quota counter: `N / 10 запросов`
- Input disabled when quota = 0, resets next day

---

## Bot Changes (minimal)

### `bot/keyboards.py`
Add `WebAppInfo` button to main menu keyboard:
```python
InlineKeyboardButton(
    text="🌐 Открыть приложение",
    web_app=WebAppInfo(url=settings.MINIAPP_URL)
)
```

### `bot/handlers/start.py`
At the end of onboarding (after pet creation confirmed), append:
```
🤖 Управляй через бота — команды прямо в чате
🌐 Или открой удобный интерфейс — всё то же самое, красиво

[Открыть приложение 🌐]
```

### `app/config.py`
Add `MINIAPP_URL: str` setting.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| initData expired (>1h) | 401 → "Закрой и открой приложение заново" |
| initData invalid signature | 401 → same message |
| JWT expired, refresh fails | Silent logout → re-open app flow |
| Network unavailable | Toast "Нет соединения", retry button |
| AI quota exhausted | Counter shows `0/10`, input disabled with label "Лимит на сегодня" |
| User never started bot | 403 → "Сначала запусти бота: @PetFeedBot" |
| No pets in profile | Redirect to deep link back to bot for onboarding |

---

## Deployment

### `railway.toml` additions
```toml
[services.miniapp.build]
buildCommand = "cd miniapp && npm install && npm run build"

[services.miniapp.deploy]
startCommand = "cd miniapp && npx serve dist -p $PORT"
restartPolicyType = "on_failure"
```

### Environment variables (miniapp)
```
VITE_API_URL=https://<backend-railway-domain>
```

### Environment variables (backend additions)
```
MINIAPP_URL=https://<miniapp-railway-domain>
JWT_SECRET=<random 256-bit secret>
JWT_ALGORITHM=HS256
ALLOWED_ORIGINS=https://<miniapp-railway-domain>
```

---

## Out of Scope

- Push notifications from Mini App (bot handles all pushes)
- Offline mode / service worker
- Pet creation flow in Mini App (stays in bot for onboarding)
- Admin panel in Mini App
- Payment / subscription UI
