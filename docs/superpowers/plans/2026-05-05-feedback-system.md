# Feedback System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hybrid feedback survey (rating + feature choice + open text) accessible via main menu button and automatic 7-day trigger, with results visible in the admin panel.

**Architecture:** Bot FSM collects 3-step input and POST-s to a new `/v1/feedback` FastAPI endpoint that writes to `user_feedback` table. The scheduler sends an auto-invite on day 7 after registration. Admin panel gets a read-only page showing all responses with summary stats.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy async, APScheduler, Alembic, Jinja2, httpx, pytest

---

## File Map

| Action | File |
|---|---|
| Create | `app/models/user_feedback.py` |
| Create | `alembic/versions/e4f5a6b7c8d9_add_user_feedback.py` |
| Create | `app/routers/feedback.py` |
| Create | `bot/handlers/feedback.py` |
| Create | `app/templates/admin/feedback.html` |
| Create | `tests/test_feedback.py` |
| Modify | `app/models/__init__.py` |
| Modify | `app/main.py` |
| Modify | `bot/states.py` |
| Modify | `bot/keyboards.py` |
| Modify | `bot/main.py` |
| Modify | `app/scheduler.py` |
| Modify | `app/routers/admin.py` |

---

## Task 1: UserFeedback model + migration

**Files:**
- Create: `app/models/user_feedback.py`
- Create: `alembic/versions/e4f5a6b7c8d9_add_user_feedback.py`
- Modify: `app/models/__init__.py`
- Test: `tests/test_feedback.py`

- [ ] **Step 1: Write failing model test**

```python
# tests/test_feedback.py
from app.models.user_feedback import UserFeedback


def test_user_feedback_model():
    fb = UserFeedback(user_id=1, rating=5, top_feature="Рацион питания", source="manual")
    assert fb.user_id == 1
    assert fb.rating == 5
    assert fb.top_feature == "Рацион питания"
    assert fb.comment is None
    assert fb.source == "manual"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
python -m pytest tests/test_feedback.py::test_user_feedback_model -v
```

Expected: `ModuleNotFoundError: No module named 'app.models.user_feedback'`

- [ ] **Step 3: Create model**

```python
# app/models/user_feedback.py
from datetime import datetime
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_feedback_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    top_feature: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), server_default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Register model in `app/models/__init__.py`**

Add this line to the existing imports in `app/models/__init__.py`:

```python
from app.models.user_feedback import UserFeedback  # noqa: F401
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_feedback.py::test_user_feedback_model -v
```

Expected: `PASSED`

- [ ] **Step 6: Create migration**

```python
# alembic/versions/e4f5a6b7c8d9_add_user_feedback.py
"""add_user_feedback

Revision ID: e4f5a6b7c8d9
Revises: d1e2f3a4b5c6
Create Date: 2026-05-05 00:01:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.SmallInteger(), nullable=False),
        sa.Column('top_feature', sa.String(length=100), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), server_default='manual', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_user_feedback_rating'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_feedback_user'),
    )


def downgrade() -> None:
    op.drop_table('user_feedback')
```

- [ ] **Step 7: Commit**

```bash
git add app/models/user_feedback.py app/models/__init__.py \
        alembic/versions/e4f5a6b7c8d9_add_user_feedback.py \
        tests/test_feedback.py
git commit -m "feat: add UserFeedback model and migration"
```

---

## Task 2: FastAPI endpoint POST /v1/feedback

**Files:**
- Create: `app/routers/feedback.py`
- Modify: `app/main.py`
- Test: `tests/test_feedback.py`

- [ ] **Step 1: Write failing endpoint test**

Add to `tests/test_feedback.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.feedback import submit_feedback
from app.models.user_feedback import UserFeedback


class TestSubmitFeedback:
    def test_invalid_rating_rejected(self):
        from pydantic import ValidationError
        from app.routers.feedback import FeedbackCreate
        with pytest.raises(ValidationError):
            FeedbackCreate(rating=6, top_feature="Рацион питания")

    def test_valid_payload_accepted(self):
        from app.routers.feedback import FeedbackCreate
        fb = FeedbackCreate(rating=5, top_feature="Напоминания", comment="Отлично!", source="auto_7d")
        assert fb.rating == 5
        assert fb.source == "auto_7d"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_feedback.py::TestSubmitFeedback -v
```

Expected: `ModuleNotFoundError: No module named 'app.routers.feedback'`

- [ ] **Step 3: Create endpoint**

```python
# app/routers/feedback.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.models.user_feedback import UserFeedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    top_feature: str
    comment: str | None = None
    source: str = "manual"


@router.post("", status_code=201)
async def submit_feedback(data: FeedbackCreate, request: Request,
                          db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(
        telegram_id=request.state.telegram_id
    )
    existing = (
        await db.execute(select(UserFeedback).where(UserFeedback.user_id == user.id))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"error": "already_submitted"})
    db.add(UserFeedback(
        user_id=user.id,
        rating=data.rating,
        top_feature=data.top_feature,
        comment=data.comment,
        source=data.source,
    ))
    await db.commit()
    return {"status": "ok"}
```

- [ ] **Step 4: Register router in `app/main.py`**

Add import and include_router call. Find the existing block of imports and includes:

```python
# Add import after existing router imports:
from app.routers import users, pets, nutrition, reminders, ai, weight, breeds, meal, feedback

# Add after existing app.include_router calls (before admin):
app.include_router(feedback.router, prefix="/v1")
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_feedback.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/routers/feedback.py app/main.py tests/test_feedback.py
git commit -m "feat: add POST /v1/feedback endpoint"
```

---

## Task 3: Bot FSM states + keyboards

**Files:**
- Modify: `bot/states.py`
- Modify: `bot/keyboards.py`

- [ ] **Step 1: Add `FeedbackFlow` to `bot/states.py`**

Append after the existing `MealBuilder` class:

```python
class FeedbackFlow(StatesGroup):
    waiting_rating  = State()
    waiting_feature = State()
    waiting_comment = State()
```

- [ ] **Step 2: Add feedback keyboards to `bot/keyboards.py`**

Append these three functions at the end of `bot/keyboards.py`:

```python
def feedback_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 1",     callback_data="fb_rating:1"),
            InlineKeyboardButton(text="⭐⭐ 2",   callback_data="fb_rating:2"),
            InlineKeyboardButton(text="⭐⭐⭐ 3", callback_data="fb_rating:3"),
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐ 4",   callback_data="fb_rating:4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐ 5", callback_data="fb_rating:5"),
        ],
    ])


def feedback_feature_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Рацион питания",      callback_data="fb_feature:Рацион питания")],
        [InlineKeyboardButton(text="⏰ Напоминания",          callback_data="fb_feature:Напоминания")],
        [InlineKeyboardButton(text="⚖️ Трекер веса",          callback_data="fb_feature:Трекер веса")],
        [InlineKeyboardButton(text="🤖 AI-ассистент",         callback_data="fb_feature:AI-ассистент")],
        [InlineKeyboardButton(text="🚫 Стоп-лист продуктов", callback_data="fb_feature:Стоп-лист продуктов")],
    ])


def feedback_comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить →", callback_data="fb_skip_comment")],
    ])
```

- [ ] **Step 3: Add feedback button to `main_menu_keyboard` in `bot/keyboards.py`**

In the `main_menu_keyboard` function, find the `rows +=` block and add the feedback button before `+ Добавить питомца`:

```python
def main_menu_keyboard(pet_name: str = "") -> InlineKeyboardMarkup:
    rows = []
    if pet_name:
        rows.append([InlineKeyboardButton(text=f"🐾 {pet_name} ▼", callback_data="menu:switch_pet")])
    rows += [
        [InlineKeyboardButton(text="Рацион питания",       callback_data="menu:nutrition")],
        [InlineKeyboardButton(text="Что нельзя давать",    callback_data="menu:stoplist")],
        [InlineKeyboardButton(text="Напоминания",           callback_data="menu:reminders")],
        [InlineKeyboardButton(text="Обновить вес",          callback_data="menu:weight")],
        [InlineKeyboardButton(text="Заказать корм",         callback_data="menu:order")],
        [InlineKeyboardButton(text="Задать вопрос AI",      callback_data="menu:ai")],
        [InlineKeyboardButton(text="Профиль питомца",       callback_data="menu:pet")],
        [InlineKeyboardButton(text="💬 Обратная связь",     callback_data="menu:feedback")],
        [InlineKeyboardButton(text="+ Добавить питомца",    callback_data="add_pet")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 4: Commit**

```bash
git add bot/states.py bot/keyboards.py
git commit -m "feat: add FeedbackFlow states and feedback keyboards"
```

---

## Task 4: Bot feedback handler

**Files:**
- Create: `bot/handlers/feedback.py`
- Modify: `bot/main.py`

- [ ] **Step 1: Create `bot/handlers/feedback.py`**

```python
# bot/handlers/feedback.py
import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards import (
    feedback_rating_keyboard, feedback_feature_keyboard,
    feedback_comment_keyboard, main_menu_keyboard,
)
from bot.states import FeedbackFlow
from app.config import settings

router = Router()


@router.callback_query(F.data == "menu:feedback")
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackFlow.waiting_rating)
    await callback.message.edit_text(
        "💬 <b>Обратная связь</b>\n\nКак оцениваешь PetFeed?",
        parse_mode="HTML",
        reply_markup=feedback_rating_keyboard(),
    )


@router.callback_query(F.data == "feedback_start")
async def start_feedback_auto(callback: CallbackQuery, state: FSMContext):
    await state.update_data(fb_source="auto_7d")
    await state.set_state(FeedbackFlow.waiting_rating)
    await callback.message.answer(
        "💬 <b>Оставь отзыв</b>\n\nКак оцениваешь PetFeed?",
        parse_mode="HTML",
        reply_markup=feedback_rating_keyboard(),
    )


@router.callback_query(F.data.startswith("fb_rating:"), FeedbackFlow.waiting_rating)
async def handle_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(fb_rating=rating)
    await state.set_state(FeedbackFlow.waiting_feature)
    await callback.message.edit_text(
        f"Оценка: {'⭐' * rating}\n\n<b>Какую функцию используешь чаще всего?</b>",
        parse_mode="HTML",
        reply_markup=feedback_feature_keyboard(),
    )


@router.callback_query(F.data.startswith("fb_feature:"), FeedbackFlow.waiting_feature)
async def handle_feature(callback: CallbackQuery, state: FSMContext):
    feature = callback.data.split(":", 1)[1]
    await state.update_data(fb_feature=feature)
    await state.set_state(FeedbackFlow.waiting_comment)
    await callback.message.edit_text(
        "Отлично! 👍\n\n<b>Что хочешь улучшить или добавить?</b>\n\n"
        "Напиши свободным текстом или нажми «Пропустить».",
        parse_mode="HTML",
        reply_markup=feedback_comment_keyboard(),
    )


@router.message(FeedbackFlow.waiting_comment)
async def handle_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    await _submit(
        telegram_id=message.from_user.id,
        data=data,
        comment=message.text.strip(),
        reply_fn=message.answer,
        pet_name=data.get("active_pet_name", ""),
    )
    await state.clear()


@router.callback_query(F.data == "fb_skip_comment", FeedbackFlow.waiting_comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await _submit(
        telegram_id=callback.from_user.id,
        data=data,
        comment=None,
        reply_fn=lambda text, **kw: callback.message.edit_text(text, **kw),
        pet_name=data.get("active_pet_name", ""),
    )
    await state.clear()


async def _submit(telegram_id: int, data: dict, comment: str | None, reply_fn, pet_name: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/feedback",
            json={
                "rating": data.get("fb_rating", 3),
                "top_feature": data.get("fb_feature", ""),
                "comment": comment,
                "source": data.get("fb_source", "manual"),
            },
            headers={"X-Telegram-Id": str(telegram_id)},
        )

    if resp.status_code == 409:
        text = "Ты уже оставлял отзыв, спасибо! Если хочешь добавить — напиши в поддержку."
    elif resp.status_code == 201:
        text = "Спасибо! Твой отзыв помогает нам стать лучше 🙏"
    else:
        text = "Что-то пошло не так. Попробуй позже."

    await reply_fn(text, reply_markup=main_menu_keyboard(pet_name))
```

- [ ] **Step 2: Register router in `bot/main.py`**

```python
# bot/main.py — full updated file
import asyncio
import logging
import os
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from app.config import settings
from app.scheduler import start_scheduler
from bot.handlers import start, pet_creation, nutrition, reminders, ai_handler, weight, meal_builder, feedback

logging.basicConfig(level=logging.INFO)


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
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    asyncio.run(main())
```

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/feedback.py bot/main.py
git commit -m "feat: add feedback bot handler with 3-step FSM"
```

---

## Task 5: Scheduler — 7-day auto-trigger

**Files:**
- Modify: `app/scheduler.py`

- [ ] **Step 1: Add `send_feedback_requests` function to `app/scheduler.py`**

Add after `check_and_send_reminders` function (before `start_scheduler`):

```python
async def send_feedback_requests():
    if _bot is None:
        return
    from datetime import date, timedelta
    from sqlalchemy import cast, Date
    from app.models.user import User
    from app.models.user_feedback import UserFeedback

    target_date = date.today() - timedelta(days=7)
    engine = create_async_engine(settings.async_database_url, connect_args={"ssl": _ssl_ctx})
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        already_submitted = select(UserFeedback.user_id)
        stmt = (
            select(User)
            .where(
                cast(User.created_at, Date) == target_date,
                User.is_active.is_(True),
                ~User.id.in_(already_submitted),
            )
        )
        users = (await session.execute(stmt)).scalars().all()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Оставить отзыв", callback_data="feedback_start")]
        ])

        for user in users:
            try:
                await _bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "Привет! Ты уже неделю с нами 🐾\n\n"
                        "Расскажи, как тебе PetFeed? Займёт 30 секунд "
                        "и поможет нам сделать бота лучше."
                    ),
                    reply_markup=kb,
                )
            except Exception as e:
                logger.warning(f"Feedback request failed for {user.telegram_id}: {e}")

    await engine.dispose()
```

Note: `select` is already imported at the top of scheduler.py via sqlalchemy — verify, or add:
```python
from sqlalchemy import select
```

- [ ] **Step 2: Register job in `start_scheduler`**

In `start_scheduler`, add the new job after the reminders job:

```python
def start_scheduler(bot):
    set_bot(bot)
    scheduler.add_job(check_and_send_reminders, "cron", minute="*", id="reminders")
    scheduler.add_job(send_feedback_requests, "cron", hour=12, minute=0, id="feedback_requests")
    scheduler.start()
    logger.info("Scheduler started")
```

- [ ] **Step 3: Commit**

```bash
git add app/scheduler.py
git commit -m "feat: add 7-day auto-trigger for feedback requests"
```

---

## Task 6: Admin panel — feedback page

**Files:**
- Modify: `app/routers/admin.py`
- Create: `app/templates/admin/feedback.html`

- [ ] **Step 1: Add import and route to `app/routers/admin.py`**

Add import at the top with existing model imports:

```python
from app.models.user_feedback import UserFeedback
```

Add route at the end of `app/routers/admin.py`:

```python
@router.get("/feedback", response_class=HTMLResponse)
async def feedback_list(request: Request, db: AsyncSession = Depends(get_db)):
    if not check_auth(request):
        return RedirectResponse("/admin/login")
    rows = (
        await db.execute(
            select(UserFeedback).order_by(UserFeedback.created_at.desc())
        )
    ).scalars().all()
    total = len(rows)
    avg_rating = round(sum(r.rating for r in rows) / total, 2) if total else 0
    feature_counts: dict[str, int] = {}
    for r in rows:
        feature_counts[r.top_feature] = feature_counts.get(r.top_feature, 0) + 1
    return templates.TemplateResponse(request, "admin/feedback.html", {
        "rows": rows,
        "total": total,
        "avg_rating": avg_rating,
        "feature_counts": feature_counts,
    })
```

- [ ] **Step 2: Create `app/templates/admin/feedback.html`**

```html
{% extends "admin/base.html" %}
{% block title %} — Обратная связь{% endblock %}
{% block content %}
<h1>Обратная связь ({{ total }})</h1>

<div style="display:flex;gap:32px;margin-bottom:24px;">
    <div style="background:#f0f4ff;padding:16px 24px;border-radius:8px;">
        <div style="font-size:13px;color:#666;">Средняя оценка</div>
        <div style="font-size:28px;font-weight:700;">{{ avg_rating }} ⭐</div>
    </div>
    {% for feature, count in feature_counts.items()|sort(attribute='1', reverse=True) %}
    <div style="background:#f0fdf4;padding:16px 24px;border-radius:8px;">
        <div style="font-size:13px;color:#666;">{{ feature }}</div>
        <div style="font-size:28px;font-weight:700;">{{ count }}</div>
    </div>
    {% endfor %}
</div>

<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>User ID</th>
            <th>Оценка</th>
            <th>Топ-фича</th>
            <th>Комментарий</th>
            <th>Источник</th>
            <th>Дата</th>
        </tr>
    </thead>
    <tbody>
        {% for r in rows %}
        <tr>
            <td>{{ r.id }}</td>
            <td>{{ r.user_id }}</td>
            <td>{{ '⭐' * r.rating }}</td>
            <td>{{ r.top_feature }}</td>
            <td>{{ (r.comment or '—')[:100] }}</td>
            <td><span class="badge {{ 'badge-on' if r.source == 'manual' else 'badge-off' }}">{{ r.source }}</span></td>
            <td>{{ r.created_at.strftime('%d.%m.%Y %H:%M') if r.created_at else '—' }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/admin.py app/templates/admin/feedback.html
git commit -m "feat: add /admin/feedback page with summary stats"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Button in main menu | Task 3 — `main_menu_keyboard` updated |
| Auto-trigger on day 7 | Task 5 — `send_feedback_requests` scheduler job |
| Step 1: rating 1-5 via buttons | Task 3 — `feedback_rating_keyboard`, Task 4 handler |
| Step 2: top feature via buttons | Task 3 — `feedback_feature_keyboard`, Task 4 handler |
| Step 3: open text with skip | Task 4 — `handle_comment` + `skip_comment` |
| One submission per user (UNIQUE) | Task 1 — model constraint, Task 2 — 409 response |
| source field: manual / auto_7d | Task 1 — model, Task 4 — `fb_source` state data |
| Admin page with summary | Task 6 — route + template |
| Error handling (bot blocked) | Task 5 — try/except in scheduler |
| Error handling (already submitted) | Task 4 — 409 mapped to message |
| FSM cleared after completion | Task 4 — `state.clear()` after submit |
| DB model + migration | Task 1 |

**Placeholder scan:** No TBDs, all code blocks complete.

**Type consistency:** `FeedbackFlow` defined in `bot/states.py` (Task 3), imported in `bot/handlers/feedback.py` (Task 4). `FeedbackCreate` defined in `app/routers/feedback.py` (Task 2), used only there. `UserFeedback` defined in `app/models/user_feedback.py` (Task 1), imported in `app/routers/feedback.py`, `app/routers/admin.py`, `app/scheduler.py`. All consistent.
