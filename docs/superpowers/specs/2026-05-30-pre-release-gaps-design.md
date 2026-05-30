# Pre-Release Gaps — Design Spec
_Date: 2026-05-30_

## Scope

Five targeted fixes required before public launch of PetFeed. No new features — only closing gaps that block release or significantly harm UX.

---

## 1. SSL Fix (`app/database.py`)

**Problem:** `ssl_ctx.verify_mode = ssl.CERT_NONE` and `ssl_ctx.check_hostname = False` disable certificate validation. Railway provides a valid TLS certificate — skipping verification is unnecessary and insecure in production.

**Change:** Make SSL conditional on `ENV`. In production (`ENV=production`), pass `ssl=True` to `create_async_engine` via `connect_args`. In development, keep `ssl=False` (or omit) so local PostgreSQL without TLS continues to work. Remove the insecure `ssl_ctx` object entirely.

**Files:** `app/database.py`

---

## 2. VITE_API_URL for Railway Build

**Problem:** `VITE_API_URL` and `VITE_BOT_USERNAME` are Vite build-time variables baked into the JS bundle. If they are not set as environment variables in Railway's miniapp service at build time, the bundle ships with empty `BASE_URL` and all API requests fail silently.

**Change:** Document and verify that Railway miniapp service has the following build-time env vars set:
- `VITE_API_URL` → URL of the deployed API service (e.g. `https://petfeed-api.railway.app`)
- `VITE_BOT_USERNAME` → `PetFeedBot` (or the actual registered username)

No code changes required. The `miniapp/.env.example` already documents these. Confirm they are set in Railway dashboard before deploying.

**Files:** `miniapp/.env.example` (add a note), `miniapp/railway.toml` (confirm buildCommand passes env)

---

## 3. TabBar — Revised Navigation

**Problem:** The miniapp has 7 pages but TabBar only exposes 4. Meal and Weight are reachable only via Home cards; AI is not reachable from the UI at all.

**New TabBar (4 tabs):**

| Tab | Icon | Route |
|-----|------|-------|
| Главная | 🏠 | `/` |
| Рацион | 🍽 | `/nutrition` |
| Кормление | 📋 | `/meal` |
| Напоминания | ⏰ | `/reminders` |

**Home page additions:**
- **Profile card** at the top: pet name, species emoji, weight, goal. Tapping opens `/profile`.
- **AI button** below nutrition card: "Спросить AI 🤖" → navigates to `/ai`.
- Weight card remains as-is (navigates to `/weight`).

**Removed from TabBar:** Profile tab (was 👤). The `/profile` route stays accessible via the Home profile card.

**TabBar hide rule:** Already hides on `/ai`. Also hide on `/meal` detail views if any full-screen subpages are added in future. No change needed now.

**Files:** `miniapp/src/components/TabBar.tsx`, `miniapp/src/pages/Home.tsx`

---

## 4. `/help` Command in Bot

**Problem:** The bot only handles `/start`. Users who get lost have no way to get oriented without restarting the flow.

**Implementation:** Add a `CommandHelp` handler in `bot/handlers/start.py` (same file, no new file needed).

**Message content:**
```
🐾 PetFeed — умный помощник для питания питомца

Что умею:
• 🍽 Рассчитать суточный рацион по весу, возрасту и породе
• ⏰ Напоминать о кормлении в нужное время
• 📋 Вести дневник кормлений
• ⚖️ Следить за изменением веса
• 🤖 Отвечать на вопросы о питании (AI, 10 запросов/день)

Как начать:
/start — создать профиль питомца или вернуться в меню

Мини-приложение с удобным интерфейсом доступно через кнопку в меню.
```

Register `/help` in BotFather after deployment with description "Что умеет бот и как им пользоваться".

**Files:** `bot/handlers/start.py`

---

## 5. Privacy Policy — `/privacy` Route in Miniapp

**Problem:** Telegram requires a Privacy Policy URL when registering a Mini App via BotFather. Without it, the Mini App cannot be officially registered.

**Content (minimum required by Telegram):**
- What data is collected: Telegram user ID, pet profile data entered by the user
- Purpose: personalising feeding recommendations
- Storage: data stored in PetFeed's database, not shared with third parties
- Contact: latyshevalex361@gmail.com

**Implementation:**
- New page `miniapp/src/pages/Privacy.tsx` — static text, no API calls
- Route added to `App.tsx` **outside** the `AuthProvider`-gated `AppRoutes` component, as a top-level `<Route path="/privacy" element={<Privacy />} />` so Telegram can fetch it without a valid session
- Link to `/privacy` added in `miniapp/src/pages/Profile.tsx` at the bottom
- The Privacy Policy URL submitted to BotFather after deployment: `https://<deployed-miniapp-url>/privacy`

**Files:** `miniapp/src/pages/Privacy.tsx`, `miniapp/src/App.tsx`, `miniapp/src/pages/Profile.tsx`

---

## Implementation Order

1. SSL fix — single-line change, zero risk
2. VITE_API_URL — Railway dashboard config, no code
3. `/help` command — small bot handler addition
4. TabBar redesign — miniapp UI refactor
5. Privacy Policy page — new static page + route

---

## Out of Scope

- CI/CD pipeline (post-launch)
- Error boundary in React (post-launch)
- Any Фаза 2 features
