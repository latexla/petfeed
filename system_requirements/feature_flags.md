# Feature Flags — PetFeed v1.0

## Концепция

Feature flags — глобальные переключатели функций системы. Хранятся в БД и кэшируются в Redis. Позволяют включать/выключать любой модуль без перезапуска сервера — через Admin Panel или SQL-командой.

**Принцип:** если флаг выключен → API возвращает `{"error": "feature_disabled", "feature": "feature_name"}` с HTTP 503.

---

## Таблица флагов в БД

```sql
CREATE TABLE feature_flags (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(100)    NOT NULL UNIQUE,
    name        VARCHAR(255)    NOT NULL,
    description TEXT,
    is_enabled  BOOLEAN         NOT NULL DEFAULT TRUE,
    updated_by  VARCHAR(255),
    updated_at  TIMESTAMP       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feature_flags_key ON feature_flags(key);
```

---

## Полный список флагов

| Ключ | Название | Описание | По умолчанию |
|---|---|---|---|
| `feature_pet_profile` | Профиль питомца | Создание и редактирование профиля | ✅ ON |
| `feature_nutrition` | Рекомендации по питанию | Расчёт рациона и стоп-лист | ✅ ON |
| `feature_reminders` | Напоминания о кормлении | Push-уведомления через Telegram | ✅ ON |
| `feature_feeding_log` | Журнал кормлений | Ведение дневника кормлений | ✅ ON |
| `feature_weight_tracking` | Трекер веса | Внесение веса и динамика | ✅ ON |
| `feature_ai_assistant` | AI-ассистент | Вопросы через DeepSeek API | ✅ ON |
| `feature_orders` | Заказ корма | Переходы к партнёрам и реферальные ссылки | ✅ ON |
| `feature_partner_webhook` | Webhook партнёров | Приём уведомлений о заказах от партнёров | ✅ ON |
| `feature_subscription` | Подписка Premium | Платная подписка и снятие лимитов | ❌ OFF |
| `feature_multi_pet` | Несколько питомцев | Более 1 питомца на аккаунт | ✅ ON |
| `feature_food_scanner` | Сканер корма | Анализ состава корма по фото/названию | ❌ OFF |
| `feature_vet_referral` | Реферал ветклиники | Раздел "Рекомендовано ветеринаром" | ❌ OFF |
| `feature_admin_panel` | Admin Panel | Веб-интерфейс администратора | ✅ ON |
| `feature_partner_catalog` | Каталог партнёров | Показ товаров нескольких партнёров | ✅ ON |

---

## Тестовые данные SQL

```sql
INSERT INTO feature_flags (key, name, description, is_enabled) VALUES
    ('feature_pet_profile',     'Профиль питомца',           'Создание и редактирование профиля питомца',        TRUE),
    ('feature_nutrition',       'Рекомендации по питанию',   'Расчёт рациона, нормы калорий и стоп-лист',        TRUE),
    ('feature_reminders',       'Напоминания о кормлении',   'Push-уведомления через Telegram Bot API',           TRUE),
    ('feature_feeding_log',     'Журнал кормлений',          'Ведение дневника фактических кормлений',            TRUE),
    ('feature_weight_tracking', 'Трекер веса',               'Внесение веса и отслеживание динамики',             TRUE),
    ('feature_ai_assistant',    'AI-ассистент',              'Ответы на вопросы через DeepSeek API',              TRUE),
    ('feature_orders',          'Заказ корма',               'Реферальные ссылки и переходы к партнёрам',         TRUE),
    ('feature_partner_webhook', 'Webhook партнёров',         'Приём уведомлений об оформленных заказах',          TRUE),
    ('feature_subscription',    'Подписка Premium',          'Платная подписка, снятие лимитов AI-запросов',      FALSE),
    ('feature_multi_pet',       'Несколько питомцев',        'Более 1 питомца на аккаунт',                        TRUE),
    ('feature_food_scanner',    'Сканер корма',              'Анализ состава корма по фото или названию',         FALSE),
    ('feature_vet_referral',    'Реферал ветклиники',        'Интеграция с ветеринарными клиниками',              FALSE),
    ('feature_admin_panel',     'Admin Panel',               'Веб-интерфейс управления контентом и партнёрами',   TRUE),
    ('feature_partner_catalog', 'Каталог партнёров',         'Показ товаров от нескольких партнёров',             TRUE);
```

---

## Реализация в Backend API

### Утилита проверки флага (Python)

```python
import redis
from functools import wraps
from fastapi import HTTPException

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
CACHE_TTL = 60  # секунд

def get_flag(key: str) -> bool:
    cached = redis_client.get(f"ff:{key}")
    if cached is not None:
        return cached == "1"
    # Fallback на БД
    from app.db import SessionLocal
    with SessionLocal() as db:
        flag = db.query(FeatureFlag).filter_by(key=key).first()
        value = flag.is_enabled if flag else False
        redis_client.setex(f"ff:{key}", CACHE_TTL, "1" if value else "0")
        return value

def require_feature(feature_key: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not get_flag(feature_key):
                raise HTTPException(
                    status_code=503,
                    detail={"error": "feature_disabled", "feature": feature_key}
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Использование в роутерах

```python
@router.post("/pets")
@require_feature("feature_pet_profile")
async def create_pet(...):
    ...

@router.get("/nutrition/{pet_id}")
@require_feature("feature_nutrition")
async def get_ration(...):
    ...

@router.post("/orders")
@require_feature("feature_orders")
async def create_order(...):
    ...

@router.post("/ai/ask")
@require_feature("feature_ai_assistant")
async def ask_ai(...):
    ...
```

---

## Как включить/выключить флаг

### Через SQL (быстро)
```sql
-- Выключить AI-ассистента
UPDATE feature_flags SET is_enabled = FALSE, updated_by = 'admin', updated_at = NOW()
WHERE key = 'feature_ai_assistant';

-- Включить подписку
UPDATE feature_flags SET is_enabled = TRUE, updated_by = 'admin', updated_at = NOW()
WHERE key = 'feature_subscription';
```

### Через Admin Panel
Раздел **Settings → Feature Flags** — таблица со всеми флагами и тогглом ON/OFF.

### Сброс кэша Redis после изменения
```bash
redis-cli DEL ff:feature_ai_assistant
```
*(или автоматически — Admin Panel инвалидирует кэш при сохранении)*

---

## Связь флагов с фазами разработки

| Флаг | MVP | Фаза 2 | Фаза 3 |
|---|---|---|---|
| `feature_pet_profile` | ✅ | ✅ | ✅ |
| `feature_nutrition` | ✅ | ✅ | ✅ |
| `feature_reminders` | ✅ | ✅ | ✅ |
| `feature_feeding_log` | ✅ | ✅ | ✅ |
| `feature_weight_tracking` | ✅ | ✅ | ✅ |
| `feature_ai_assistant` | ✅ | ✅ | ✅ |
| `feature_orders` | ✅ | ✅ | ✅ |
| `feature_partner_webhook` | ✅ | ✅ | ✅ |
| `feature_multi_pet` | ✅ | ✅ | ✅ |
| `feature_food_scanner` | ❌ | ✅ | ✅ |
| `feature_subscription` | ❌ | ✅ | ✅ |
| `feature_vet_referral` | ❌ | ❌ | ✅ |

---

*Документ создан: 2026-04-18*
*Связанные артефакты: petfeed_backend.md, petfeed_sql.sql, c4_Level_2_containers_diagram_PetFeed_v1.plantuml*
