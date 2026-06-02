# Дизайн: Коммерческие корма (commercial_foods)

**Дата:** 2026-06-01
**Статус:** Утверждён, готов к планированию
**Связано с:** BL-002 (рацион), BL-005 (AI), meal-builder

## Цель

Добавить структурированную базу ~30–50 курируемых коммерческих кормов, которая:

1. Даёт **точные КБЖУ** в конструкторе рациона (meal builder) — заменяет DeepSeek-фолбэк для известных кормов.
2. Питает **новый экран подбора** в боте и **контекст AI-ассистента** — подбор/сравнение кормов по виду, возрасту, размеру породы и состоянию здоровья.

Вся фича закрывается фичефлагом `feature_food_catalog`, чтобы её можно было отключить.

## Вне объёма (YAGNI)

- Заказы и реферальные ссылки (BL-004), цены, фасовки.
- Автоимпорт из Open Pet Food Facts и парсинг сайтов (структура к импорту готова через поля `barcode`/`source`, но сам импорт не делаем).
- Полнотекстовый/векторный поиск — достаточно fuzzy по name/aliases/brand.

## Источник данных

Решение: **ручной curated seed** на старте. Внешние источники (Open Pet Food Facts — единственный открытый, ODbL; KibbleLab/KibbleWatcher/Chewy — проприетарные) не дают нужной точности «из коробки»: производители публикуют «гарантированный анализ» (белок min %, жир min %, клетчатка max %, влага, зола), а не КБЖУ на 100 г; углеводы не указываются, калорийность (ME) — отдельно. Поэтому первая загрузка делается вручную с разовой конвертацией, а структура таблицы заложена под будущий импорт.

**Конвертация в сиде (как есть, на 100 г):**

- `protein_g`, `fat_g` ≈ значения «гарантированного анализа».
- `carb_g` (NFE) = `100 − protein − fat − fiber − moisture − ash`.
- `kcal_per_100g` = ME с упаковки, иначе модифицированный Атуотер.
- Каждая строка снабжается комментарием-источником.

## Архитектура

### 1. Модель данных — таблица `commercial_foods`

| Поле | Тип | Назначение |
|---|---|---|
| `id` | int PK | |
| `brand` | str(80) | Royal Canin, Pro Plan, Hills… |
| `name` | str(120) | линейка/продукт: «Sterilised 37» |
| `name_aliases` | Text (JSON) | для fuzzy-поиска, как в `food_items` |
| `species` | str(20) | cat/dog/rodent/bird/reptile |
| `food_type` | str(20) | dry/wet — словарь из `food_categories` |
| `life_stage` | str(20) | junior/adult/senior/all |
| `breed_size` | str(20), null | mini/medium/large/all (в основном собаки) |
| `condition_tags` | Text (JSON) | `["sterilised","sensitive","weight_control","hypoallergenic","renal","urinary"]` |
| `kcal_per_100g` | Numeric(6,2) | КБЖУ на 100 г «как есть» |
| `protein_g`, `fat_g`, `carb_g` | Numeric(5,2) | |
| `calcium_mg`, `phosphorus_mg`, `omega3_mg`, `taurine_mg` | Numeric(7,2), null | микро, как в `food_items` |
| `source` | str(40) | `manufacturer` / `openpetfoodfacts` |
| `barcode` | str(20), null | задел под будущий импорт |

Таблица создаётся через существующий `create_all` в lifespan (как и остальные модели). Регистрируется в `app/models/__init__.py`.

### 2. Сид `app/seeds/commercial_foods_seed.py`

~30–50 топ-кормов РФ-рынка (кошки/собаки × сухой/влажный × возраст × состояния), по образцу `food_items_seed.py`. Guard от дублей при повторном запуске (проверка по `brand`+`name` перед вставкой). Запуск: `python -m app.seeds.commercial_foods_seed`.

### 3. Репозиторий `CommercialFoodRepository`

- `get_all() -> list[CommercialFood]`
- `search(q, species, limit=10)` — по `name` + `name_aliases` + `brand`, фильтр по `species in [species,"all"]` (паттерн `MealRepository.search_food_items`).
- `get_by_id(id)`
- `filter(species, food_type=None, life_stage=None, breed_size=None, tags=None, limit, offset)` — для экрана подбора с пагинацией.

### 4. Сервис `CommercialFoodService`

- `pet_to_filters(pet, breed_risks) -> filters`: `age_months → life_stage` (порог junior/senior по виду), `breed → breed_size` (через breed_registry/эвристику веса), `breed_risks + goal → condition_tags` (например `goal=lose → weight_control`, риск `urinary/renal → соответствующий тег`).
- `rank(foods, filters) -> list` — ранжирование по числу совпавших осей.

### 5. Интеграция в конструктор рациона

`MealService.lookup_product`: после поиска в `food_items` искать в `commercial_foods` (fuzzy, тот же `search_food_item`-подход), **до** DeepSeek-фолбэка. Возврат `FoodLookupResult(source="commercial_db")`. Добавление в дневник — через существующий путь «по нутриентам» в `meal.py` (он уже умеет добавлять продукт без `food_item_id`). Поиск в `commercial_foods` пропускается, если флаг выключен.

### 6. Контекст AI-ассистента

`ai_service.ask`: при наличии питомца подмешать в контекст компактный список топ-N (≈3–5) подходящих кормов (из `CommercialFoodService.pet_to_filters` + `filter`), формат «бренд — название, ккал/100 г, для кого». Бюджет токенов маленький. Пропускается при выключенном флаге.

### 7. Новый экран подбора в боте

- FSM `FoodPicker` в `bot/states.py` + хэндлер `bot/handlers/food_picker.py` + клавиатуры в `bot/keyboards.py` (паттерн `MealBuilder`).
- Вход: кнопка «🔎 Подобрать корм» в меню питомца (показывается только при включённом флаге).
- Поток: фильтры предзаполнены из профиля питомца (вид, life_stage по возрасту, breed_size) → пользователь сужает по типу/состоянию → пагинированный список (бренд + название + ккал) → карточка корма (КБЖУ, для кого, теги).
- API: `GET /v1/commercial-foods` с query-фильтрами (`species`, `food_type`, `life_stage`, `breed_size`, `tag`, `q`, `limit`, `offset`), аутентификация `X-Telegram-Id`. Эндпоинт возвращает 403/404 при выключенном флаге.

### 8. Фичефлаг `feature_food_catalog` + хелпер проверки

В коде **сейчас нет** проверки фичефлагов — таблица `feature_flags` существует только с переключателем в админке. Поэтому в рамках задачи:

- Добавить `app/services/feature_flag_service.py` (или `app/utils/feature_flags.py`): `async def is_enabled(key, db) -> bool` — читает `FeatureFlag.is_enabled`, кэширует в Redis TTL 60 сек (как описано в CLAUDE.md), дефолт `True`, если записи нет.
- Завести запись флага `feature_food_catalog` (через сид/админку).
- Гейтить: API-эндпоинт `/v1/commercial-foods`, кнопку бота, ветку в `lookup_product` и подмешивание в AI-контекст.

Хелпер пишется обобщённо, чтобы переиспользоваться для остальных 14 флагов в будущем (не делаем сейчас больше необходимого, но API универсальный).

## Тесты

По образцу `tests/test_meal_service.py`:

- Мат-баланс КБЖУ в сиде: `|(4·prot + 9·fat + 4·carb) − kcal| / kcal ≤ 0.15` (как `MealService._validate_math`).
- `CommercialFoodService.pet_to_filters` — корректный маппинг возраст/порода/риски/цель → фильтры.
- `rank` — порядок по совпавшим осям.
- `lookup_product` находит коммерческий корм раньше DeepSeek (мок DeepSeek не вызывается).
- `is_enabled` — кэш Redis, дефолт True, off отключает ветки.

## Открытые риски

- Качество конвертации «гарантированного анализа» → КБЖУ зависит от данных производителя; помечаем `source` и держим консервативные значения.
- Маппинг `breed → breed_size` опирается на существующий breed_registry/вес; при отсутствии данных → `breed_size=null`/`all`, фильтр не сужает.
