# MealBuilder — Подбор порции кормления

**Дата:** 2026-05-02  
**Статус:** Согласован  
**Фаза:** MVP (Фаза 1)

---

## Цель

Позволить пользователю в диалоге с ботом составить порцию на одно кормление. Бот проверяет каждый продукт по стоп-листу, считает КБЖУ и ключевые микронутриенты, рекомендует что добавить, пока норма не закрыта. В конце — итоговая сводка.

---

## Два входа в флоу

1. **Из напоминания о кормлении** — кнопка «🍽 Что дать?» добавляется к пуш-сообщению APScheduler. Только если у питомца есть активные напоминания.
2. **Из раздела «Питание»** — кнопка «Подобрать порцию» в нижней части экрана рациона (`bot/handlers/nutrition.py`).

Оба входа запускают один и тот же FSM-флоу `MealBuilder`.

---

## Пользовательский путь

```
[Вход] → выбор типа кормления → ввод продуктов (диалог) → итоговая сводка
```

**Шаг 1 — выбор типа:**
Кнопки: `[🥩 Натуралка]` `[🥫 Корм]` `[🔀 Смешанное]`

**Шаг 2 — ввод продуктов (итеративно):**
- Пользователь вводит продукт текстом: «курица», «гречка», «яйцо»
- После каждого ввода бот отвечает: результат поиска + прогресс нормы + рекомендация что добавить
- Кнопки: `[✅ Готово]` `[↩ Отменить последний]`
- Если продукт в стоп-листе Level 1 — блокируем, объясняем почему
- Если Level 2 — предупреждаем, даём выбор `[Да, добавить]` `[Нет, заменить]`
- При первом запросе показываем примеры продуктов для выбранного типа кормления

**Шаг 3 — итоговая сводка:**
Список продуктов с граммовкой, нутриентная таблица, Ca:P соотношение, gap-предупреждения, финальный совет.

---

## Архитектура

### Новая таблица: `food_items`

```sql
id            SERIAL PRIMARY KEY
name          VARCHAR(100) NOT NULL          -- «курица варёная»
name_aliases  TEXT                           -- JSON array: ["курочка","chicken","куриное"]
category      VARCHAR(50) NOT NULL           -- meat|grain|vegetable|egg|dairy|fish|oil
species       VARCHAR(50) NOT NULL           -- dog|cat|all
kcal_per_100g NUMERIC(6,2) NOT NULL
protein_g     NUMERIC(5,2) NOT NULL
fat_g         NUMERIC(5,2) NOT NULL
carb_g        NUMERIC(5,2) NOT NULL
calcium_mg    NUMERIC(7,2)
phosphorus_mg NUMERIC(7,2)
omega3_mg     NUMERIC(7,2)
taurine_mg    NUMERIC(7,2)
source        VARCHAR(50) DEFAULT 'USDA'    -- 'USDA' | 'deepseek_cache'
```

~70 записей из USDA FoodData Central, загружаются seed-скриптом `app/seeds/food_items_seed.py`.

### Сессия в Redis

```
key:  meal:{telegram_id}:{pet_id}
TTL:  30 минут

{
  "food_type": "natural",
  "items": [
    {"name": "курица", "grams": 120, "kcal": 150, "protein_g": 25.0,
     "fat_g": 3.2, "carb_g": 0, "calcium_mg": 11, "phosphorus_mg": 200, "omega3_mg": 50, "taurine_mg": 0},
    ...
  ],
  "target": {"kcal": 250, "protein_g": 30, "fat_g": 8, "calcium_mg": 130, "phosphorus_mg": 200}
}
```

Список хранится в Redis, не в FSM-данных — чтобы не раздувать state при длинных сессиях.

### Профиль нутриентов питомца

`meal_service.get_required_micros(pet, breed_risks)` возвращает список нутриентов для отслеживания — без дублирования знаний из `nutrition_knowledge` и `breed_risks`:

```python
SPECIES_MICROS = {
    "cat":     ["taurine_mg", "omega3_mg", "calcium_mg", "phosphorus_mg"],
    "dog":     ["omega3_mg", "calcium_mg", "phosphorus_mg"],
    "rodent":  ["calcium_mg", "phosphorus_mg"],
    "bird":    ["calcium_mg"],
    "reptile": ["calcium_mg", "phosphorus_mg"],
}

RISK_BOOST = {
    "atopy":             ["omega3_mg"],
    "patellar_luxation": ["omega3_mg"],
}
```

Итоговый summary показывает только релевантные для этого питомца микронутриенты.

---

## Пайплайн обработки продукта

Каждый продукт проходит шаги строго по порядку:

### Шаг 1 — Стоп-лист (блокирует до расчёта)

1. `rapidfuzz` против `stop_foods.product_name` (порог 75%)
2. Проверка по `name_aliases` продукта (чтобы «виноград» → нашёл «изюм»)
3. **Level 1** → блокируем, продукт не добавляется, сообщаем токсичный компонент
4. **Level 2** → предупреждаем, предлагаем `[Да, добавить]` `[Нет, заменить]`
5. **Level 3** → информируем, добавляем

### Шаг 2 — Поиск КБЖУ

1. `rapidfuzz` против `food_items.name` + `food_items.name_aliases` (порог 80%) — приоритет
2. Не найдено → DeepSeek `deepseek-chat`:
   - Промпт запрашивает structured JSON: `{kcal, protein_g, fat_g, carb_g, calcium_mg, phosphorus_mg, omega3_mg, taurine_mg, category, confidence}`
   - **Range Guard**: проверяем ккал в диапазоне для категории продукта
   - **Math Guard**: `protein_g×4 + fat_g×9 + carb_g×4 ≈ kcal ±15%`
   - `confidence < 0.7` → добавляем ⚠️ к ответу пользователю
   - Кэш в Redis 24ч, `source = "deepseek_cache"`

### Диапазоны Range Guard

| Категория  | ккал/100г |
|------------|-----------|
| meat       | 80–400    |
| fish       | 80–300    |
| egg        | 130–160   |
| grain      | 300–380   |
| vegetable  | 15–100    |
| dairy      | 30–400    |
| oil        | 700–900   |

### Шаг 3 — Прогресс и рекомендация

После добавления продукта считаем gap до нормы одного кормления (`ration.daily_*/meals_per_day`):

```
gap_kcal    = target_kcal    - Σ items.kcal
gap_protein = target_protein - Σ items.protein_g
gap_fat     = target_fat     - Σ items.fat_g
ca_p_ratio  = Σ calcium_mg / Σ phosphorus_mg  (норма 1.2–1.4)
```

Рекомендуем продукт из `food_items` WHERE `species IN (pet.species, "all")`, с наибольшим покрытием главного gap-а.

**Стоп-условие:** `gap_kcal < 10% AND gap_protein < 10%` → «Норма закрыта ✅», предлагаем `[Показать итог]`.

---

## Итоговая сводка

```
🍽 Порция для {pet.name} (1 кормление)

Курица варёная — 120г
Гречка         —  55г
Яйцо           —  30г
──────────────────────
Итого: 205г

Энергия: 246 / 250 ккал (98%) ✅
Белок:    28 / 30 г    (95%) ✅
Жир:       8 / 8 г    (100%) ✅
Ca:P:    1.3:1              ✅
Омега-3: 48мг (норма >50мг) ⚠️

💡 Добавь ½ ч.л. льняного масла для восполнения Омега-3

⚠️ Расчёт приблизительный. Проконсультируйся с ветеринаром.
```

Набор строк нутриентов определяется `get_required_micros(pet, breed_risks)` — только релевантные для вида и рисков породы.

---

## Новые компоненты

### Backend

| Файл | Действие | Назначение |
|------|----------|------------|
| `app/models/food_item.py` | CREATE | Модель таблицы `food_items` |
| `app/seeds/food_items_seed.py` | CREATE | ~70 записей из USDA |
| `app/services/meal_service.py` | CREATE | Поиск, стоп-лист, расчёт, рекомендации, валидация |
| `app/repositories/meal_repo.py` | CREATE | Запросы к `food_items`, `stop_foods`, Redis-сессия |
| `app/routers/meal.py` | CREATE | `POST /v1/meal/add-product`, `GET /v1/meal/summary/{pet_id}`, `DELETE /v1/meal/reset/{pet_id}` |
| `alembic/versions/xxxx_add_food_items.py` | CREATE | Миграция |
| `app/models/__init__.py` | MODIFY | +FoodItem |
| `app/main.py` | MODIFY | +router meal |

### Bot

| Файл | Действие | Назначение |
|------|----------|------------|
| `bot/handlers/meal_builder.py` | CREATE | Весь FSM-диалог MealBuilder |
| `bot/states.py` | MODIFY | +`MealBuilder.waiting_type`, `waiting_product` |
| `bot/keyboards.py` | MODIFY | +`meal_type_keyboard()`, `meal_progress_keyboard()`, `meal_confirm_stop_keyboard()` |
| `bot/handlers/reminders.py` | MODIFY | +кнопка «🍽 Что дать?» в пуш APScheduler |
| `bot/handlers/nutrition.py` | MODIFY | +кнопка «Подобрать порцию» под экраном рациона |
| `bot/main.py` | MODIFY | +router meal_builder |

### Тесты

| Файл | Покрытие |
|------|----------|
| `tests/test_meal_service.py` | rapidfuzz-поиск, Range Guard, Math Guard, стоп-лист проверка, расчёт gap-ов, get_required_micros |

---

## API контракты

### POST /v1/meal/add-product
```json
Request:  { "pet_id": 1, "product_name": "курица", "food_type": "natural" }
Response: {
  "status": "added" | "blocked" | "warning",
  "item": { "name": "курица варёная", "grams": 120, "kcal": 150, ... },
  "progress": { "kcal_pct": 60, "protein_pct": 85, "fat_pct": 40 },
  "done": false,
  "recommendation": "Добавь гречку или яйцо — не хватает углеводов и жиров",
  "warning": null
}
```

### GET /v1/meal/summary/{pet_id}
```json
Response: {
  "items": [...],
  "totals": { "kcal": 246, "protein_g": 28, "fat_g": 8, "calcium_mg": 130, "phosphorus_mg": 200, "omega3_mg": 48 },
  "targets": { "kcal": 250, "protein_g": 30, ... },
  "ca_p_ratio": 1.3,
  "gaps": { "omega3_mg": -2 },
  "tip": "Добавь ½ ч.л. льняного масла для Омега-3",
  "required_micros": ["omega3_mg", "calcium_mg", "phosphorus_mg"]
}
```

---

## Расчёт граммовки порции

Пользователь не вводит граммы вручную — бот считает их автоматически:

```
suggested_grams = clamp(gap_kcal_remaining × 0.5 / (kcal_per_100g / 100), 20, 200)
```

- Берём 50% оставшегося kcal-gap → переводим в граммы через калорийность продукта
- `clamp(20, 200)` — минимум 20г (осмысленная порция), максимум 200г (не перекормить одним продуктом)
- При первом продукте gap = 100% нормы → получается ~40–60% нормы в граммах

Пример: норма 250 ккал, первый продукт курица (150 ккал/100г):  
`250 × 0.5 / 1.5 = 83г` → clamp → 83г ≈ 125 ккал (50% нормы)

---

## Ограничения MVP

- Виды с полным покрытием: **dog**, **cat**. Остальные (rodent, bird, reptile) — базовые микро (Ca, P).
- DeepSeek-fallback расходует AI-лимит (10/день бесплатно). Кэш 24ч снижает нагрузку.
- `name_aliases` заполняются вручную при seed; расширение синонимов через DeepSeek — Фаза 2.

---

## Упрощение: удаление расчёта граммовки из рациона

MealBuilder делает `daily_food_grams` бессмысленным — реальные граммы зависят от конкретных продуктов, а не от усреднённого kcal/100g. Поэтому вместе с этой фичей делаем следующие изменения:

### Что убираем

| Компонент | Изменение |
|-----------|-----------|
| `Pet.food_category_id` | Удалить поле из модели и схемы |
| `PetCreation` FSM шаг 9 «Чем кормите?» | Удалить — становится 8 шагов |
| `NutritionService` — расчёт `daily_food_grams` | Удалить, `kcal_per_100g` больше не нужен |
| `Ration.daily_food_grams`, `Ration.food_per_meal_grams` | Сделать nullable (миграция), не заполнять |
| Отображение граммовки в `bot/handlers/nutrition.py` | Убрать строки «Корма в день» и «Порция за раз» |

### Что остаётся в рационе

Рацион теперь показывает только **цели**:
```
Рацион для Барона
Калорий в день:  420 ккал
Кормлений:       2 раза в день
Белок (минимум): 28 г/день
Жир  (минимум):  8 г/день
Ca:P оптимум:    1.2–1.4:1
```

Граммы конкретной еды — только через «Подобрать порцию» (MealBuilder).

### Дополнительные файлы к изменению

| Файл | Действие |
|------|----------|
| `app/models/pet.py` | Удалить `food_category_id` |
| `app/schemas/pet.py` | Удалить `food_category_id` из `PetCreate`/`PetUpdate`/`PetResponse` |
| `app/services/nutrition_service.py` | Удалить `food_category_id` логику и `daily_food_grams` расчёт |
| `app/repositories/nutrition_repo.py` | Удалить `get_food_category()` вызов из `calculate_and_save` |
| `bot/handlers/pet_creation.py` | Удалить `waiting_food_category` шаг и обработчики |
| `bot/keyboards.py` | Удалить `food_category_keyboard()` |
| `bot/states.py` | Удалить `waiting_food_category` из `PetCreation` |
| `bot/handlers/nutrition.py` | Убрать строки граммовки из `_show_ration()` |
| `alembic/versions/xxxx_...` | `food_category_id` DROP из pets, nullable на rations |
