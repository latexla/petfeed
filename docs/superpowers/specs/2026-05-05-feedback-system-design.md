# Feedback System — Design Spec

**Date:** 2026-05-05  
**Status:** Approved  
**Feature flag:** none (always available)

---

## Goal

Collect structured user feedback to support investor conversations and product decisions. Two entry points: manual button in the main menu, automatic trigger on day 7 after registration.

---

## User Flow

```
Entry point (manual or auto-7d)
  │
  ▼
Step 1 — Rating
  "Как оцениваешь PetFeed?"
  Inline buttons: [⭐ 1] [⭐⭐ 2] [⭐⭐⭐ 3] [⭐⭐⭐⭐ 4] [⭐⭐⭐⭐⭐ 5]
  │
  ▼
Step 2 — Top feature
  "Какую функцию используешь чаще всего?"
  Inline buttons:
    [Рацион] [Напоминания] [Трекер веса]
    [AI-ассистент] [Стоп-лист продуктов]
  │
  ▼
Step 3 — Open comment
  "Что хочешь улучшить или добавить? (можно пропустить)"
  Free text input  |  [Пропустить]
  │
  ▼
Confirmation: "Спасибо! Твой отзыв помогает нам стать лучше 🙏"
```

**Rules:**
- User can only submit feedback once (duplicate check on `user_id`). If already submitted: "Ты уже оставлял отзыв, спасибо!"
- Пропустить on step 3 saves `comment = NULL`.
- FSM is cleared after submission or if user sends /cancel at any step.

---

## Architecture

### New files
- `bot/handlers/feedback.py` — FSM handler for the 3-step survey
- `app/models/user_feedback.py` — SQLAlchemy model
- `alembic/versions/<id>_add_user_feedback.py` — migration

### Modified files
- `bot/states.py` — add `FeedbackFlow` with 3 states
- `bot/keyboards.py` — add "Обратная связь 💬" button to main menu keyboard
- `bot/main.py` — register feedback router
- `app/scheduler.py` — add daily job for 7-day auto-trigger
- `app/routers/admin.py` — add `/admin/feedback` page (list of responses)

---

## Data Model

```sql
CREATE TABLE user_feedback (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating      SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    top_feature VARCHAR(100) NOT NULL,
    comment     TEXT,
    source      VARCHAR(20) NOT NULL DEFAULT 'manual',  -- 'manual' | 'auto_7d'
    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);
```

---

## FSM States

```python
class FeedbackFlow(StatesGroup):
    waiting_rating   = State()
    waiting_feature  = State()
    waiting_comment  = State()
```

---

## Auto-trigger (Scheduler)

- Job name: `send_feedback_request`
- Schedule: daily at 12:00 UTC
- Logic:
  1. Query users where `created_at::date = now()::date - 7`
  2. Exclude users who already have a row in `user_feedback`
  3. Send message + inline button "Оставить отзыв" to each `telegram_id`
- Source field saved as `'auto_7d'`

---

## Admin Panel Page

Route: `GET /admin/feedback`  
Displays table: user_id, rating, top_feature, comment (truncated to 100 chars), source, created_at.  
Summary row at top: average rating, count by top_feature, total submissions.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| User sends unexpected text during step 1/2 | Re-send the question with buttons |
| User already submitted feedback | "Ты уже оставлял отзыв, спасибо! Если хочешь добавить — напиши в поддержку." |
| Scheduler fails to reach user (bot blocked) | Catch `TelegramForbiddenError`, log, skip silently |
| DB write fails | Log error, clear FSM, reply "Что-то пошло не так, попробуй позже" |

---

## Out of Scope

- Editing submitted feedback
- Per-question analytics dashboard (admin page shows raw data only)
- Email/export of feedback
