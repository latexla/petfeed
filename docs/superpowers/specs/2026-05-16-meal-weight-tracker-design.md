# Meal Tracker + Weight Tracker — Design Spec

**Date:** 2026-05-16  
**Status:** Approved  
**Feature flag:** none (always available)

---

## Goal

Add two missing Mini App features to match all bot functionality:
1. **Meal Tracker** — daily food diary with product search, real-time КБЖУ progress, composite quality scoring based on existing NRC 2006 norms, and persistent history in DB
2. **Weight Tracker** — weight updates with line chart history and trend display

Both are accessible from Home page cards — no tabbar changes.

---

## User Flow

### Meal Tracker

```
Home → tap "🍖 Питание сегодня" card → /meal

/meal page:
  ┌─ Today's summary ─────────────────────────────┐
  │  180 / 320 ккал  ████████░░░░ 56%             │
  │  Б: 28г  Ж: 12г  Кальций: 74%  Омега-3: 60%  │
  │  🟡 Оценка дня: 61 / 100                       │
  │  💡 Маловато белка и омега-3                   │
  └────────────────────────────────────────────────┘

  ┌─ Add product ──────────────────────────────────┐
  │  🔍 [Найди продукт...                        ] │
  │  Results: Куриная грудка 165 ккал/100г          │
  │           Куриная печень  136 ккал/100г         │
  │  → tap → [___ г]  [+ Добавить]                 │
  └────────────────────────────────────────────────┘

  ┌─ Added today ──────────────────────────────────┐
  │  Куриная грудка  150г  248 ккал           [✕]  │
  │  Рис варёный      50г   65 ккал           [✕]  │
  └────────────────────────────────────────────────┘

  ┌─ Last 7 days ──────────────────────────────────┐
  │  🟢 Пт  92/100  315/320 ккал                   │
  │  🟡 Чт  61/100  240/320 ккал                   │
  │  🔴 Ср  38/100  180/320 ккал                   │
  └────────────────────────────────────────────────┘

  [🗑 Сбросить день]
```

**Day rollover:** When user opens `/meal` and the Redis session date ≠ today → auto-save yesterday's session to `feeding_sessions` DB → start fresh session for today.

### Weight Tracker

```
Home → tap "⚖️ Вес" card → /weight

/weight page:
  Current: 4.2 кг
  [____ кг]  [Обновить]

  📈 LineChart — last 10 entries (recharts)

  History table:
  16 мая  4.2 кг  ▼ -0.1 кг
  09 мая  4.3 кг  ▼ -0.2 кг
  02 мая  4.5 кг
```

---

## Quality Scoring System

### Inputs
- **Targets** (min): from `ration.daily_calories`, `ration.protein_min_g`, `ration.fat_min_g`, `MealService.compute_micro_targets()` (NRC 2006 per species)
- **Upper limits** (max): from `MICRO_MAX_PER_1000KCAL` (NRC MTL), `MER_MAX_OVERAGE = 0.20`
- **Actuals**: from meal session totals

### Score Calculation (0–100)

Each factor scored 0–100, then weighted average:

| Factor | Weight | Species |
|---|---|---|
| Calories | 35% | all |
| Protein | 25% | all |
| Fat | 20% | all |
| Calcium | 10% | all |
| Taurine | 10% | cat only |
| Omega-3 | 10% | cat, dog |
| Phosphorus | 5% | all |

Weights are normalized to sum to 100% per species.

**Per-factor scoring:**
```
ratio = actual / target_min

ratio in [0.90, 1.10]  → 100 pts  (optimal)
ratio in [0.75, 0.90)  → 70 pts   (slightly low)
ratio in (1.10, 1.30]  → 70 pts   (slightly high)
ratio in [0.50, 0.75)  → 40 pts   (low)
ratio in (1.30, NRC_MTL/target] → 40 pts (high)
ratio < 0.50           → 0 pts    (critical deficit)
ratio > NRC_MTL/target → 0 pts    (exceeds safe limit)
```

**Quality label:**
- `good` — score ≥ 80
- `ok`   — score 50–79
- `poor` — score < 50

**Tips generation** — reuses `MealService.check_upper_limits()` and `get_summary_tip()`. Examples:
- "Недоел 140 ккал — добавь 70г куриной грудки"
- "Маловато омега-3 — добавь рыбы или рыбьего жира"
- "⚠️ Много кальция — превышен NRC MTL"
- "Рацион разнообразный 👍"

---

## Data Model

### New table: `feeding_sessions`

```sql
CREATE TABLE feeding_sessions (
    id           SERIAL PRIMARY KEY,
    pet_id       INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    total_kcal   NUMERIC(7,2) NOT NULL DEFAULT 0,
    protein_g    NUMERIC(6,2) NOT NULL DEFAULT 0,
    fat_g        NUMERIC(6,2) NOT NULL DEFAULT 0,
    calcium_pct  NUMERIC(5,1),
    phosphorus_pct NUMERIC(5,1),
    taurine_pct  NUMERIC(5,1),
    omega3_pct   NUMERIC(5,1),
    kcal_pct     NUMERIC(5,1),
    items_count  INTEGER NOT NULL DEFAULT 0,
    score        SMALLINT NOT NULL DEFAULT 0,
    quality      VARCHAR(10) NOT NULL,   -- 'good' | 'ok' | 'poor'
    tips         TEXT,                   -- JSON array of tip strings
    UNIQUE (pet_id, session_date)
);
```

### Alembic migration
- `alembic/versions/XXXX_add_feeding_sessions.py`

### SQLAlchemy model
- `app/models/feeding_session.py`

---

## Backend Changes

### New: `app/services/meal_service.py` additions

```python
def compute_quality(
    totals: dict,          # actual consumed: kcal, protein_g, fat_g, calcium_mg, ...
    target: dict,          # from existing compute_micro_targets() + ration.daily_calories
    pet_species: str,
    breed_risks: list[str],
) -> tuple[int, str, list[str]]:
    """
    Returns (score 0-100, quality label, tips list).
    Uses existing compute_micro_targets(), MICRO_MAX_PER_1000KCAL,
    check_upper_limits(), get_summary_tip().
    target dict is built from:
      - ration.daily_calories (from NutritionService.calculate_and_save())
      - MealService.compute_micro_targets() for micros
    """
```

### New: `app/models/feeding_session.py`
SQLAlchemy mapped class for `feeding_sessions` table.

### Modified: `app/routers/meal.py`

**New endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/meal/food-search` | `?q=str&species=str` — ILIKE search on `food_items.name` and `food_items.name_aliases`, returns top 10 results |
| `GET` | `/v1/meal/history/{pet_id}` | Last 30 days from `feeding_sessions`, ordered by date desc |

**Modified: `POST /v1/meal/add-product`**  
Before adding product, check session date:
```python
if session and session.get("date") != today:
    await save_session_to_db(session, pet, db)
    session = None  # start fresh
```

**Modified: `GET /v1/meal/summary/{pet_id}`**  
Same day-rollover check. Returns existing `progress` dict plus new `quality_score`, `quality_label`, `tips`.

### Modified: `app/scheduler.py`

New daily job at 00:05 UTC:
```python
async def save_daily_sessions():
    """Save all Redis meal sessions from yesterday to feeding_sessions DB."""
```

---

## Frontend Changes

### New: `miniapp/src/api/meal.ts`

```typescript
interface FoodSearchResult {
  id: number; name: string; category: string;
  kcal_per_100g: number; protein_g: number; fat_g: number; carb_g: number;
}
interface MealSummary {
  items: MealItem[]; target: Record<string, number>;
  progress: Record<string, number>;  // actual values
  quality_score: number; quality_label: 'good' | 'ok' | 'poor'; tips: string[];
}
interface MealHistoryEntry {
  session_date: string; total_kcal: number; score: number;
  quality: 'good' | 'ok' | 'poor'; kcal_pct: number;
}

searchFood(q: string, species: string): Promise<FoodSearchResult[]>
addProduct(petId, productName, grams, foodType): Promise<MealSummary>
getSummary(petId): Promise<MealSummary>
resetSession(petId): Promise<void>
undoLast(petId): Promise<void>
getHistory(petId): Promise<MealHistoryEntry[]>
```

### New: `miniapp/src/api/weight.ts`

```typescript
interface WeightEntry { weight_kg: number; recorded_at: string; }
interface WeightUpdateResponse {
  pet_id: number; old_weight: number; new_weight: number; ration_recalculated: boolean;
}

updateWeight(petId, weightKg): Promise<WeightUpdateResponse>
getHistory(petId): Promise<WeightEntry[]>
```

### New: `miniapp/src/hooks/useMealSession.ts`
Manages meal session state: summary, search results, add/undo/reset actions.

### New: `miniapp/src/hooks/useWeightHistory.ts`
Fetches weight history + handles update.

### New components

| File | Responsibility |
|---|---|
| `components/MealSummaryCard.tsx` | Home card: ккал progress + quality badge |
| `components/WeightCard.tsx` | Home card: current weight + last delta |
| `components/ProgressBar.tsx` | Reusable horizontal progress bar with color |
| `components/QualityBadge.tsx` | 🟢/🟡/🔴 circle + score number |
| `components/WeightChart.tsx` | recharts LineChart, last 10 entries |

### New pages

| File | Route | Content |
|---|---|---|
| `pages/Meal.tsx` | `/meal` | Summary card, search, items list, history |
| `pages/Weight.tsx` | `/weight` | Update form, chart, history table |

### Modified: `pages/Home.tsx`
Add `MealSummaryCard` and `WeightCard` between NutritionCard and AI button.
Both cards load data lazily (show skeleton on load, don't block page).

### Modified: `App.tsx`
Add routes: `<Route path="/meal" element={<Meal />} />`  
`<Route path="/weight" element={<Weight />} />`

### New dependency
```json
"recharts": "^2.12.0"
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| No ration calculated yet | `/meal` shows "Сначала рассчитай рацион в боте" |
| food-search returns empty | "Продукт не найден — попробуй другое название" |
| Weight update fails validation (≤0) | Inline error under input |
| Session save to DB fails | Log error, keep Redis session, retry next open |
| Scheduler fails to save session | Log + skip; session will be saved next time user opens app |

---

## Out of Scope

- Meal templates / saved meals
- Barcode/photo food scanning (Phase 2 feature)
- Multi-day analytics dashboard
- Manual editing of past feeding sessions
- Feeding reminders linked to meal tracker
