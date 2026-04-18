# PetFeed — Project Context for Claude

## Что это за проект
Telegram-бот + мобильное приложение для владельцев домашних животных.
Помогает правильно кормить питомца: персональный рацион, напоминания о кормлении, заказ корма через партнёров, AI-ассистент.

**Рабочее название:** PetFeed  
**Слоган:** "Один бот — любой питомец"  
**Статус:** MVP в разработке — реализованы BL-001, BL-002, BL-003, multi-pet

---

## Стек технологий
| Компонент | Технология |
|---|---|
| Telegram Bot | Python 3.12 + aiogram 3 |
| Backend API | FastAPI |
| База данных | PostgreSQL 15 |
| Кэш / FSM | Redis |
| AI-ассистент | DeepSeek API (deepseek-chat) |
| Планировщик | APScheduler |
| Admin Panel | FastAPI + Jinja2 |

---

## Ключевые решения
- **Старт через Telegram** (не мобильное приложение) — минимальный барьер входа
- **Feature flags** для всех модулей — таблица `feature_flags` в PostgreSQL, кэш в Redis TTL 60 сек
- **Монетизация** — партнёрская комиссия 5–15% с заказов корма (старт), подписка Premium 299₽/мес (Фаза 2)
- **AI** — DeepSeek вместо Claude (дешевле в 10–20 раз), кэш ответов в Redis TTL 24ч
- **Multi-pet** — несколько питомцев на аккаунт включено (`feature_multi_pet = ON`)
- **AI лимит** — 10 запросов/день бесплатно

---

## Животные (species enum)
`cat`, `dog`, `rodent`, `bird`, `reptile`

## Цели кормления (goal enum)
`maintain`, `lose`, `gain`, `growth`

## Статусы заказов (status enum)
`pending`, `confirmed`, `cancelled`

---

## Структура БД (реализовано)
`users` → `pets` → `rations`, `feeding_reminders`, `nutrition_knowledge`, `feature_flags`  
Ещё в схеме (не реализованы): `weight_history`, `feeding_logs`, `partners`, `products`, `orders`, `ai_requests`

Полная схема: `system_requirements/petfeed_sql.sql`  
ERD: `system_requirements/petfeed_erd.plantuml`

---

## Feature Flags (14 флагов)
MVP включены (ON): `feature_pet_profile`, `feature_nutrition`, `feature_reminders`, `feature_feeding_log`, `feature_weight_tracking`, `feature_ai_assistant`, `feature_orders`, `feature_partner_webhook`, `feature_admin_panel`, `feature_partner_catalog`, `feature_multi_pet`

Фаза 2 (OFF): `feature_food_scanner`, `feature_subscription`, `feature_vet_referral`

Полный список: `system_requirements/feature_flags.md`

---

## FSM бота (aiogram 3 States)
- `PetCreation` — 7 состояний: species → breed → name → **age_unit** → age → weight → confirm
  - `waiting_age_unit` — новый шаг: выбор единицы возраста (месяцы / годы)
- `ReminderSetup` — 1 состояние (waiting_times)
- `WeightUpdate` — 1 состояние
- `AiQuestion` — 1 состояние

FSM хранится в Redis, ключ `fsm:{telegram_id}`, TTL 30 минут.  
Детали: `system_requirements/bot_fsm.md`

---

## API (FastAPI, prefix /v1) — реализовано
| Роутер | Эндпоинты | Статус |
|---|---|---|
| `/users` | GET /me | ✅ |
| `/pets` | POST, GET, GET /{id}, PUT /{id} | ✅ |
| `/nutrition` | GET /{pet_id} | ✅ |
| `/reminders` | POST, GET /{pet_id} | ✅ |
| `/weight` | — | ⏳ |
| `/orders` | — | ⏳ |
| `/ai` | — | ⏳ |

Аутентификация: `X-Telegram-Id` (пользователи), `X-Api-Key` (партнёры), `X-Admin-Token` (admin)

---

## Бизнес-логика
- `BL-001` ✅ — Регистрация и профиль питомца (multi-pet)
- `BL-002` ✅ — Расчёт рациона (RER = 70 × weight^0.75, база знаний 14 записей)
- `BL-003` ✅ — Напоминания (APScheduler каждую минуту + Telegram push)
- `BL-004` ⏳ — Заказ корма (реферальный токен + webhook партнёра)
- `BL-005` ⏳ — AI-ассистент (DeepSeek + Redis кэш)
- `BL-006` ⏳ — Обновление веса (пересчёт рациона при изменении ≥5%)

Детали: `system_requirements/petfeed_backend.md`

---

## Структура кода (реализовано)
```
app/
├── main.py, config.py, database.py, redis_client.py, scheduler.py
├── models/       user, pet, feature_flag, ration, nutrition_knowledge, feeding_reminder
├── schemas/      user, pet
├── repositories/ user_repo, pet_repo, nutrition_repo, reminder_repo
├── services/     user_service, pet_service, nutrition_service, reminder_service
├── routers/      users, pets, nutrition, reminders
└── middleware/   auth (X-Telegram-Id)

bot/
├── main.py, states.py, keyboards.py
└── handlers/     start, pet_creation, nutrition, reminders
```

---

## Roadmap
- **Фаза 0** (нед 1–2): подготовка, окружение, кастодев
- **Фаза 1** (нед 3–8): MVP — онбординг ✅, питание ✅, напоминания ✅, AI ⏳, заказы ⏳
- **Фаза 2** (мес 3–6): трекер веса, экзотика, Premium
- **Фаза 3** (мес 7–12): мобильное приложение, федеральные партнёры

Детали: `docs/roadmap.md`
