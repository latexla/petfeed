# Дизайн: Рекомендательная система питания

**Дата:** 2026-05-22  
**Статус:** Утверждён  
**Область:** MVP для `cat` и `dog`, с архитектурным заделом на расширение

---

## 1. Проблема

Текущий Meal флоу требует от пользователя знать, что добавить — он просто ищет продукт и вводит граммы. Нет подсказки «что приготовить из того, что есть дома» и нет анализа «чего не хватает в этом готовом корме для моей породы».

---

## 2. Решение

Два режима кормления с умными рекомендациями, встроенные прямо в Meal страницу без отдельных экранов.

---

## 3. Пользовательский флоу

### Переключатель режима
В верхней части Meal страницы над полем поиска — два чипса:

```
[ 🥩 Натуральный ]  [ 🛒 Готовый корм ]
```

Выбор сохраняется в `localStorage`. По умолчанию — последний использованный.

### Натуральный режим
1. Показываются чипсы из последних 7 уникальных ингредиентов (из истории)
2. Пользователь тапает нужные + может добавить через поиск
3. Нажимает «Подобрать граммовку»
4. Система рассчитывает оптимальное соотношение ингредиентов под MER питомца
5. Показывает список с граммами + покрытие нормы + дефициты
6. Кнопка «Применить» добавляет все продукты в лог дня

### Готовый корм
1. Поле поиска (как текущий поиск в Meal)
2. После выбора продукта — показывает суточные граммы
3. Блок дефицитов: чего не хватает в этом корме для породы питомца
4. Кнопка «Применить» добавляет в лог

---

## 4. Архитектура бэкенда

### Endpoint

```
POST /v1/meal/recommend
Authorization: Bearer <token>
```

**Запрос (натуральный):**
```json
{
  "pet_id": 1,
  "mode": "natural",
  "ingredients": ["курица", "гречка", "морковь"]
}
```

**Запрос (готовый корм):**
```json
{
  "pet_id": 1,
  "mode": "commercial",
  "product_name": "Royal Canin Adult"
}
```

**Ответ:**
```json
{
  "items": [
    {
      "name": "Курица варёная",
      "grams": 120,
      "kcal": 132,
      "protein_g": 29.4,
      "fat_g": 2.9,
      "carb_g": 0.0,
      "calcium_mg": 15.6,
      "phosphorus_mg": 201.6,
      "omega3_mg": 48.0,
      "taurine_mg": 180.0,
      "food_item_id": 5  // null если продукт найден через DeepSeek, а не из БД
    }
  ],
  "totals": {
    "kcal": 250,
    "protein_g": 35.2,
    "fat_g": 5.1,
    "carb_g": 18.0,
    "calcium_mg": 280.0,
    "phosphorus_mg": 380.0,
    "omega3_mg": 120.0,
    "taurine_mg": 250.0
  },
  "targets": {
    "kcal": 265,
    "protein_g": 38.0,
    "fat_g": 8.0,
    "calcium_mg": 312.0,
    "phosphorus_mg": 250.0,
    "omega3_mg": 160.0,
    "taurine_mg": 200.0
  },
  "micro_coverage": {
    "calcium_mg": 89,
    "phosphorus_mg": 152,
    "omega3_mg": 75,
    "taurine_mg": 125
  },
  "covers_pct": 94,
  "deficiencies": ["Не хватает Омега-3 — добавь ½ ч.л. рыбьего масла"],
  "warnings": ["⚠️ Ca:P = 0.74:1 — ниже нормы 1.2:1"]
}
```

---

## 5. Нутриенты по видам

### Обязательные микронутриенты (MVP)

| Нутриент | Кошка | Собака |
|---|---|---|
| `taurine_mg` | ✅ | — |
| `omega3_mg` | ✅ | ✅ |
| `calcium_mg` | ✅ | ✅ |
| `phosphorus_mg` | ✅ | ✅ |

Дополнительно через `RISK_BOOST`: если в `breed_risks` есть `atopy` или `patellar_luxation` — усиленный контроль `omega3_mg`.

### Прочие виды (заглушка)
Для `rodent`, `bird`, `reptile` — возвращать только `items` с граммами и `covers_pct`. Поля `deficiencies` и `micro_coverage` — пустые массивы. Расширение в Фазе 2.

---

## 6. Логика бэкенда

### RecommendService

**Natural режим:**
1. Fetch pet → ration (MER, meals_per_day, protein_min_g, fat_min_g)
2. Для каждого ингредиента: `meal_service.lookup_product()` (DB → DeepSeek fallback)
3. Проверить каждый через `check_stop_list()` — если уровень 1 (fatal) → исключить и вернуть предупреждение
4. Распределить калории пропорционально весу белка каждого ингредиента
5. Рассчитать `grams` через `daily_food_grams()` для каждого
6. Собрать `totals` и сравнить с `compute_micro_targets()`
7. Сформировать `deficiencies` через `get_summary_tip()`

**Commercial режим:**
1. Fetch pet → ration
2. `lookup_product(product_name)` → получить КБЖУ на 100г
3. Суточные граммы: `(daily_calories / kcal_per_100g) * 100`
4. Рассчитать нутриенты для этих граммов
5. Сравнить с `compute_micro_targets()` по species + breed_risks
6. Сформировать `deficiencies` и `warnings` (включая Ca:P ratio)

### Переиспользуемые методы из MealService
- `lookup_product()` — поиск в БД + DeepSeek
- `check_stop_list()` — проверка стоп-листа
- `compute_micro_targets()` — целевые значения микронутриентов
- `get_required_micros()` — список нутриентов по species + breed_risks
- `get_summary_tip()` — текстовые советы по дефицитам
- `get_excess_warnings()` — предупреждения о превышении NRC MTL

---

## 7. Архитектура фронтенда

### Новые файлы

```
miniapp/src/
├── api/recommend.ts          — POST /v1/meal/recommend
├── hooks/useRecommend.ts     — состояние режима, ингредиентов, результата
└── components/RecommendBar.tsx — UI чипсы + ввод + результат
```

### Изменения в существующих файлах

- `Meal.tsx` — добавить `<RecommendBar>` над полем поиска; при "Применить" вызывать `add()` из `useMealSession` для каждого item

### `useRecommend.ts` (контракт)

```typescript
interface RecommendResult {
  items: RecommendItem[];
  totals: NutrientTotals;
  targets: NutrientTotals;
  micro_coverage: Record<string, number>;
  covers_pct: number;
  deficiencies: string[];
  warnings: string[];
}

interface UseRecommend {
  mode: 'natural' | 'commercial';
  setMode: (m: 'natural' | 'commercial') => void;
  selectedIngredients: string[];
  toggleIngredient: (name: string) => void;
  selectedProduct: FoodSearchResult | null;
  setSelectedProduct: (p: FoodSearchResult | null) => void;
  result: RecommendResult | null;
  loading: boolean;
  error: string | null;
  recommend: () => Promise<void>;
}
```

### localStorage
- Ключ `petfeed_feed_mode` — хранит `'natural' | 'commercial'`
- Ключ `petfeed_recent_ingredients` — массив последних 7 названий

---

## 8. Обработка ошибок

| Ситуация | Поведение |
|---|---|
| Ингредиент не найден в БД и DeepSeek недоступен | Пропустить ингредиент, показать "не удалось найти X" |
| Ингредиент в стоп-листе уровня 1 (fatal) | Исключить из расчёта, показать красное предупреждение |
| Pet не cat и не dog | Вернуть items с граммами, deficiencies = [] |
| Нет рациона у питомца | HTTP 400 с `"ration not found"` |
| DeepSeek timeout | HTTP 504, фронт показывает "Попробуй ещё раз" |

---

## 9. Файлы затронутые реализацией

**Backend:**
- `app/routers/meal.py` — новый POST /recommend эндпоинт
- `app/services/recommend_service.py` — новый сервис
- `app/schemas/recommend.py` — Pydantic схемы запроса/ответа

**Frontend:**
- `miniapp/src/api/recommend.ts` — новый
- `miniapp/src/hooks/useRecommend.ts` — новый
- `miniapp/src/components/RecommendBar.tsx` — новый
- `miniapp/src/pages/Meal.tsx` — изменение (добавить RecommendBar)

---

*Связанные артефакты: petfeed_backend.md (BL-002), meal_service.py, nutrition_service.py*
