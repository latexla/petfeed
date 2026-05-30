# Pre-Release Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close five pre-release gaps — SSL security, build env config, bot /help command, miniapp navigation, and Privacy Policy page.

**Architecture:** Changes span three independent layers: Python backend (`app/database.py`), Telegram bot (`bot/handlers/start.py`), and React miniapp (`miniapp/src/`). Each task is self-contained and can be committed independently.

**Tech Stack:** Python/SQLAlchemy/asyncpg, aiogram 3, React/TypeScript/React Router v6, Railway

---

## File Map

| File | Change |
|------|--------|
| `app/database.py` | Conditional SSL based on ENV |
| `miniapp/.env.example` | Add Railway build note |
| `bot/handlers/start.py` | Add CommandHelp handler |
| `miniapp/src/components/TabBar.tsx` | Replace Profile tab with Meal tab |
| `miniapp/src/pages/Home.tsx` | Make PetCard tappable → /profile |
| `miniapp/src/pages/Privacy.tsx` | New static page (create) |
| `miniapp/src/App.tsx` | Add /privacy route outside AuthProvider |
| `miniapp/src/pages/Profile.tsx` | Add link to /privacy at bottom |

---

## Task 1: SSL Fix

**Files:**
- Modify: `app/database.py`

- [ ] **Step 1: Replace insecure SSL context with conditional SSL**

Open `app/database.py` and replace the entire file content with:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

db_url = settings.async_database_url
_connect_args = {"ssl": True} if settings.ENV == "production" else {}
engine = create_async_engine(db_url, echo=False, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: Verify local dev still works**

```bash
python3 -m uvicorn app.main:app --port 8001
```

Expected: server starts without SSL errors. Hit `Ctrl+C`.

- [ ] **Step 3: Commit**

```bash
git add app/database.py
git commit -m "fix: use conditional SSL for database — enabled only in production"
```

---

## Task 2: Document VITE_API_URL for Railway

**Files:**
- Modify: `miniapp/.env.example`

- [ ] **Step 1: Add Railway build note to .env.example**

Open `miniapp/.env.example` and replace the file with:

```
# PetFeed Mini App — Environment Variables
# Copy to miniapp/.env.local for local development

# Backend API URL (no trailing slash)
VITE_API_URL=https://your-backend.railway.app

# Telegram bot username (without @)
VITE_BOT_USERNAME=PetFeedBot

# ⚠️  Railway build-time note:
# These are Vite build-time variables baked into the JS bundle.
# In Railway dashboard → miniapp service → Variables, set BOTH before deploying:
#   VITE_API_URL   = https://<your-api-service>.railway.app
#   VITE_BOT_USERNAME = PetFeedBot   (or your actual BotFather username)
# Without these, all API calls will fail silently.
```

- [ ] **Step 2: Commit**

```bash
git add miniapp/.env.example
git commit -m "docs: warn that VITE_* vars must be set in Railway before building miniapp"
```

- [ ] **Step 3: Set vars in Railway dashboard (manual)**

In Railway dashboard → miniapp service → Variables, add:
- `VITE_API_URL` = `https://<your-api-service-url>.railway.app`
- `VITE_BOT_USERNAME` = your bot's username without @

No code change required — Railway passes service variables to buildCommand automatically.

---

## Task 3: `/help` Command in Bot

**Files:**
- Modify: `bot/handlers/start.py`

- [ ] **Step 1: Add the CommandHelp import and handler**

In `bot/handlers/start.py`, add `Command` to the aiogram filters import (line 4):

```python
from aiogram.filters import Command, CommandStart
```

Then add the handler at the bottom of the file (after the last `@router` function):

```python
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🐾 <b>PetFeed</b> — умный помощник для питания питомца\n\n"
        "<b>Что умею:</b>\n"
        "• 🍽 Рассчитать суточный рацион по весу, возрасту и породе\n"
        "• ⏰ Напоминать о кормлении в нужное время\n"
        "• 📋 Вести дневник кормлений\n"
        "• ⚖️ Следить за изменением веса\n"
        "• 🤖 Отвечать на вопросы о питании (AI, 10 запросов/день)\n\n"
        "<b>Как начать:</b>\n"
        "/start — создать профиль питомца или вернуться в меню\n\n"
        "<i>Мини-приложение с удобным интерфейсом доступно через кнопку в меню.</i>",
        parse_mode="HTML",
    )
```

- [ ] **Step 2: Check for syntax errors**

```bash
python3 -c "from bot.handlers.start import router; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/start.py
git commit -m "feat: add /help command with bot capabilities overview"
```

- [ ] **Step 4: Register /help in BotFather (manual, after deploy)**

Send to @BotFather:
1. `/setcommands`
2. Select your bot
3. Send:
```
start - Открыть меню или создать профиль питомца
help - Что умеет бот и как им пользоваться
```

---

## Task 4: TabBar — Replace Profile with Meal, Make PetCard Tappable

**Files:**
- Modify: `miniapp/src/components/TabBar.tsx`
- Modify: `miniapp/src/pages/Home.tsx`

- [ ] **Step 1: Update TabBar tabs**

Replace the entire content of `miniapp/src/components/TabBar.tsx` with:

```tsx
import { useLocation, useNavigate } from 'react-router-dom';
import { c } from '../theme';

const TABS = [
  { path: '/', label: 'Главная', icon: '🏠' },
  { path: '/nutrition', label: 'Рацион', icon: '🍽' },
  { path: '/meal', label: 'Кормление', icon: '📋' },
  { path: '/reminders', label: 'Напоминания', icon: '⏰' },
];

export function TabBar() {
  const location = useLocation();
  const navigate = useNavigate();

  if (location.pathname === '/ai') return null;

  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      display: 'flex', background: c.bg,
      borderTop: `1px solid ${c.border}`, zIndex: 100,
    }}>
      {TABS.map((tab) => {
        const active = location.pathname === tab.path;
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            style={{
              flex: 1, padding: '8px 0', border: 'none', background: 'none',
              color: active ? c.accent : c.hint,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              gap: 2, fontSize: 10, cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 22 }}>{tab.icon}</span>
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Make PetCard tappable on Home → opens /profile**

Replace the entire content of `miniapp/src/pages/Home.tsx` with:

```tsx
import { useNavigate } from 'react-router-dom';
import { NutritionCard } from '../components/NutritionCard';
import { PetCard } from '../components/PetCard';
import { MealSummaryCard } from '../components/MealSummaryCard';
import { WeightCard } from '../components/WeightCard';
import { usePet } from '../contexts/PetContext';
import { useNutrition } from '../hooks/useNutrition';
import { useMealSession } from '../hooks/useMealSession';
import { useWeightHistory } from '../hooks/useWeightHistory';
import { c } from '../theme';

export function Home() {
  const { activePet, loading: petLoading, error: petError } = usePet();
  const { ration, loading: rationLoading } = useNutrition(activePet?.id ?? null);
  const { summary: mealSummary, loading: mealLoading } = useMealSession(
    activePet?.id ?? null,
    activePet?.species ?? null,
  );
  const { history: weightHistory, loading: weightLoading } = useWeightHistory(activePet?.id ?? null);
  const navigate = useNavigate();

  if (petLoading) return <div style={{ padding: 24, color: c.hint }}>Загрузка...</div>;
  if (petError) return <div style={{ padding: 24, color: c.destructive }}>{petError}</div>;
  if (!activePet) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 40 }}>
        <div style={{ fontSize: 48 }}>🐾</div>
        <p style={{ marginTop: 12, color: c.hint }}>
          Питомец не найден. Создай профиль в боте @PetFeedBot
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <div
        onClick={() => navigate('/profile')}
        style={{ cursor: 'pointer' }}
      >
        <PetCard pet={activePet} />
      </div>

      {rationLoading
        ? <div style={{ color: c.hint, fontSize: 14 }}>Загружаю рацион...</div>
        : ration && <NutritionCard ration={ration} />
      }
      {ration?.notes && (
        <div style={{ background: c.bgSecondary, borderRadius: 12, padding: 12, fontSize: 13, color: c.hint, marginBottom: 12 }}>
          {ration.notes}
        </div>
      )}

      <MealSummaryCard summary={mealSummary} loading={mealLoading} />
      <WeightCard history={weightHistory} loading={weightLoading} />

      <button
        onClick={() => navigate('/ai')}
        style={{
          width: '100%', padding: 14, background: c.accent, color: c.accentText,
          border: 'none', borderRadius: 14, fontSize: 16, fontWeight: 600, cursor: 'pointer',
        }}
      >
        🤖 AI-ассистент
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Build to check for TypeScript errors**

```bash
cd miniapp && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd ..
git add miniapp/src/components/TabBar.tsx miniapp/src/pages/Home.tsx
git commit -m "feat: replace Profile tab with Meal tab, make PetCard tappable to profile"
```

---

## Task 5: Privacy Policy Page

**Files:**
- Create: `miniapp/src/pages/Privacy.tsx`
- Modify: `miniapp/src/App.tsx`
- Modify: `miniapp/src/pages/Profile.tsx`

- [ ] **Step 1: Create the Privacy Policy page**

Create `miniapp/src/pages/Privacy.tsx` with this content:

```tsx
import type { ReactNode } from 'react';
import { c } from '../theme';

export function Privacy() {
  return (
    <div style={{ padding: 24, paddingBottom: 40, maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, color: c.text }}>
        Политика конфиденциальности
      </h1>
      <p style={{ fontSize: 12, color: c.hint, marginBottom: 24 }}>
        Последнее обновление: 30 мая 2026 г.
      </p>

      <Section title="Какие данные мы собираем">
        <p>При использовании PetFeed мы собираем:</p>
        <ul>
          <li>Telegram ID пользователя (для идентификации аккаунта)</li>
          <li>Данные о питомце, которые вы вводите сами: вид, порода, возраст, вес, цель питания, имя</li>
          <li>Записи о кормлениях и изменениях веса, которые вы добавляете</li>
          <li>Вопросы к AI-ассистенту</li>
        </ul>
      </Section>

      <Section title="Зачем мы это собираем">
        <p>
          Данные используются исключительно для работы сервиса: расчёта рациона,
          отправки напоминаний о кормлении и персонализации рекомендаций.
        </p>
      </Section>

      <Section title="Как хранятся данные">
        <p>
          Данные хранятся в защищённой базе данных на серверах Railway (ЕС/США).
          Передача данных на сервер осуществляется по зашифрованному каналу (HTTPS).
        </p>
      </Section>

      <Section title="Передача третьим лицам">
        <p>
          Мы не продаём и не передаём ваши данные третьим лицам.
          Вопросы к AI-ассистенту обрабатываются сервисом DeepSeek API согласно их
          политике конфиденциальности.
        </p>
      </Section>

      <Section title="Удаление данных">
        <p>
          Чтобы удалить все свои данные, напишите нам:{' '}
          <a href="mailto:latyshevalex361@gmail.com" style={{ color: c.accent }}>
            latyshevalex361@gmail.com
          </a>
        </p>
      </Section>

      <Section title="Контакт">
        <p>
          По вопросам конфиденциальности:{' '}
          <a href="mailto:latyshevalex361@gmail.com" style={{ color: c.accent }}>
            latyshevalex361@gmail.com
          </a>
        </p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#333' }}>
        {title}
      </h2>
      <div style={{ fontSize: 14, lineHeight: 1.7, color: '#555' }}>
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add /privacy route outside AuthProvider in App.tsx**

Replace the entire content of `miniapp/src/App.tsx` with:

```tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { c } from './theme';
import { PetProvider } from './contexts/PetContext';
import { TabBar } from './components/TabBar';
import { AI } from './pages/AI';
import { Home } from './pages/Home';
import { Meal } from './pages/Meal';
import { Nutrition } from './pages/Nutrition';
import { Privacy } from './pages/Privacy';
import { Profile } from './pages/Profile';
import { Reminders } from './pages/Reminders';
import { Weight } from './pages/Weight';

function AppRoutes() {
  const { isReady, error } = useAuth();

  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 60 }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🐾</div>
        <p style={{ color: c.hint }}>{error}</p>
      </div>
    );
  }

  if (!isReady) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 60, color: c.hint }}>
        Загрузка...
      </div>
    );
  }

  return (
    <PetProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/nutrition" element={<Nutrition />} />
        <Route path="/reminders" element={<Reminders />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/ai" element={<AI />} />
        <Route path="/meal" element={<Meal />} />
        <Route path="/weight" element={<Weight />} />
      </Routes>
      <TabBar />
    </PetProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/privacy" element={<Privacy />} />
        <Route path="*" element={
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        } />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 3: Add Privacy Policy link in Profile page**

In `miniapp/src/pages/Profile.tsx`, find this exact closing block:

```tsx
      <a
        href={`https://t.me/${BOT_USERNAME}?start=feedback`}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'block', width: '100%', padding: 14, textAlign: 'center',
          background: c.bg, border: `1.5px solid ${c.accent}`, color: c.accent,
          borderRadius: 14, fontSize: 15, fontWeight: 600, textDecoration: 'none',
        }}
      >
        💬 Оставить отзыв
      </a>
    </div>
  );
}
```

Replace it with:

```tsx
      <a
        href={`https://t.me/${BOT_USERNAME}?start=feedback`}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'block', width: '100%', padding: 14, textAlign: 'center',
          background: c.bg, border: `1.5px solid ${c.accent}`, color: c.accent,
          borderRadius: 14, fontSize: 15, fontWeight: 600, textDecoration: 'none',
        }}
      >
        💬 Оставить отзыв
      </a>

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <a
          href="/privacy"
          style={{ fontSize: 12, color: c.hint, textDecoration: 'underline' }}
        >
          Политика конфиденциальности
        </a>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Build to check for TypeScript errors**

```bash
cd miniapp && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Verify /privacy is accessible without auth**

```bash
cd miniapp && npm run dev &
sleep 3
curl -s http://localhost:3000/privacy | grep -c "конфиденциальности"
```

Expected: `1` (the word appears in the page HTML served by the dev server).

Kill the dev server: `kill %1`

- [ ] **Step 6: Commit**

```bash
cd ..
git add miniapp/src/pages/Privacy.tsx miniapp/src/App.tsx miniapp/src/pages/Profile.tsx
git commit -m "feat: add Privacy Policy page at /privacy, accessible without auth"
```

- [ ] **Step 7: Submit to BotFather (manual, after deploy)**

After deploying miniapp to Railway:
1. Open @BotFather → `/newapp` (or `/editapp` if already created)
2. Set Privacy Policy URL to: `https://<your-miniapp-url>.railway.app/privacy`
