# Nutrition Recommendation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить рекомендательную систему питания в Meal страницу miniapp: натуральный режим подбирает граммовку ингредиентов, режим готового корма показывает суточные граммы и дефициты по breed_risks.

**Architecture:** Новый `RecommendService` переиспользует методы `MealService`; два новых endpoint в `meal.py`. Фронтенд добавляет `RecommendBar` с переключателем режима над существующим поиском. Для DeepSeek-продуктов без `food_item_id` — отдельный endpoint `daily/add-named`.

**Tech Stack:** Python 3.12 / FastAPI / pytest-asyncio (backend), React 18 / TypeScript / axios (frontend), Redis (сессии), DeepSeek API (nutrition lookup).

---

## Карта файлов

| Файл | Действие | Назначение |
|---|---|---|
| `app/services/meal_service.py` | Изменить | Добавить `food_item_id` в `FoodLookupResult` |
| `app/schemas/recommend.py` | Создать | Pydantic схемы запроса/ответа |
| `app/services/recommend_service.py` | Создать | Логика рекомендаций (natural + commercial) |
| `app/routers/meal.py` | Изменить | Два новых endpoint: `/recommend` и `/daily/add-named` |
| `tests/test_recommend_service.py` | Создать | Unit-тесты RecommendService |
| `miniapp/src/api/recommend.ts` | Создать | HTTP клиент для recommend |
| `miniapp/src/hooks/useRecommend.ts` | Создать | React хук (состояние + вызов API) |
| `miniapp/src/components/RecommendBar.tsx` | Создать | UI компонент с режимами |
| `miniapp/src/pages/Meal.tsx` | Изменить | Вставить RecommendBar |

---

## Task 1: Расширить FoodLookupResult полем food_item_id

**Files:**
- Modify: `app/services/meal_service.py:96-107`

- [ ] **Шаг 1: Добавить food_item_id в датакласс**

В `meal_service.py` найди датакласс `FoodLookupResult` (строка ~94) и добавь поле:

```python
@dataclass
class FoodLookupResult:
    name: str
    grams: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    calcium_mg: float
    phosphorus_mg: float
    omega3_mg: float
    taurine_mg: float
    source: str
    confidence: float = 1.0
    low_confidence: bool = False
    food_item_id: int | None = None   # ← добавить
```

- [ ] **Шаг 2: Проставить food_item_id в lookup_product()**

В методе `lookup_product()` (строка ~180) измени ветку DB:

```python
async def lookup_product(self, product_name: str) -> FoodLookupResult | None:
    food_items = await self.repo.get_all_food_items()
    fi = self.search_food_item(product_name, food_items)
    if fi:
        return FoodLookupResult(
            name=fi.name, grams=0,
            kcal=float(fi.kcal_per_100g),
            protein_g=float(fi.protein_g),
            fat_g=float(fi.fat_g),
            carb_g=float(fi.carb_g),
            calcium_mg=float(fi.calcium_mg or 0),
            phosphorus_mg=float(fi.phosphorus_mg or 0),
            omega3_mg=float(fi.omega3_mg or 0),
            taurine_mg=float(fi.taurine_mg or 0),
            source="db",
            food_item_id=fi.id,   # ← добавить
        )
    return await self._deepseek_lookup(product_name)
```

- [ ] **Шаг 3: Проверить что тесты не сломались**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
python -m pytest tests/test_meal_service.py -v
```

Ожидаем: все зелёные.

- [ ] **Шаг 4: Коммит**

```bash
git add app/services/meal_service.py
git commit -m "feat: add food_item_id field to FoodLookupResult"
```

---

## Task 2: Pydantic схемы recommend

**Files:**
- Create: `app/schemas/recommend.py`

- [ ] **Шаг 1: Создать файл схем**

```python
# app/schemas/recommend.py
from pydantic import BaseModel
from typing import Literal


class RecommendRequest(BaseModel):
    pet_id: int
    mode: Literal["natural", "commercial"]
    ingredients: list[str] = []   # для natural: ["курица", "гречка"]
    product_name: str = ""        # для commercial: "Royal Canin Adult"


class RecommendItem(BaseModel):
    name: str
    grams: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    calcium_mg: float
    phosphorus_mg: float
    omega3_mg: float
    taurine_mg: float
    food_item_id: int | None = None


class NutrientMap(BaseModel):
    kcal: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carb_g: float = 0
    calcium_mg: float = 0
    phosphorus_mg: float = 0
    omega3_mg: float = 0
    taurine_mg: float = 0


class RecommendResponse(BaseModel):
    items: list[RecommendItem]
    totals: NutrientMap
    targets: NutrientMap
    micro_coverage: dict[str, float]   # {"calcium_mg": 89.0, ...}
    covers_pct: float
    deficiencies: list[str]
    warnings: list[str]


class DailyAddNamedRequest(BaseModel):
    pet_id: int
    name: str
    grams: float
    kcal_per_100g: float
    protein_g: float
    fat_g: float
    carb_g: float
    calcium_mg: float = 0.0
    phosphorus_mg: float = 0.0
    omega3_mg: float = 0.0
    taurine_mg: float = 0.0
```

- [ ] **Шаг 2: Коммит**

```bash
git add app/schemas/recommend.py
git commit -m "feat: add Pydantic schemas for recommendation endpoint"
```

---

## Task 3: RecommendService — тесты и реализация

**Files:**
- Create: `app/services/recommend_service.py`
- Create: `tests/test_recommend_service.py`

- [ ] **Шаг 1: Написать тесты (сначала)**

```python
# tests/test_recommend_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.recommend_service import RecommendService
from app.services.meal_service import FoodLookupResult, StopCheckResult


def _make_lookup(name: str, kcal: float, protein_g: float, fat_g: float,
                 carb_g: float = 0.0, calcium_mg: float = 100.0,
                 phosphorus_mg: float = 80.0, omega3_mg: float = 50.0,
                 taurine_mg: float = 0.0, food_item_id: int | None = None) -> FoodLookupResult:
    return FoodLookupResult(
        name=name, grams=0, kcal=kcal, protein_g=protein_g,
        fat_g=fat_g, carb_g=carb_g, calcium_mg=calcium_mg,
        phosphorus_mg=phosphorus_mg, omega3_mg=omega3_mg,
        taurine_mg=taurine_mg, source="db", food_item_id=food_item_id,
    )


def _make_pet(species: str = "dog", breed: str = "labrador",
              age_months: int = 24, weight_kg: float = 30.0):
    p = MagicMock()
    p.id = 1
    p.species = species
    p.breed = breed
    p.age_months = age_months
    p.weight_kg = weight_kg
    return p


def _make_ration(daily_calories: float = 1000.0, meals_per_day: int = 2):
    r = MagicMock()
    r.daily_calories = daily_calories
    r.meals_per_day = meals_per_day
    return r


def _make_meal_svc(lookups: dict[str, FoodLookupResult | None],
                   breed_risks: list[str] | None = None):
    svc = MagicMock()
    svc.lookup_product = AsyncMock(side_effect=lambda name: lookups.get(name))
    svc.check_stop_list = MagicMock(
        return_value=StopCheckResult(None, None, None, None)
    )
    svc.get_required_micros = MagicMock(
        return_value=["omega3_mg", "calcium_mg", "phosphorus_mg"]
    )
    svc.compute_micro_targets = MagicMock(return_value={
        "omega3_mg": 250.0, "calcium_mg": 1250.0, "phosphorus_mg": 1000.0
    })
    svc.get_summary_tip = MagicMock(return_value="")
    svc.get_excess_warnings = MagicMock(return_value=[])
    return svc


def _make_nutrition_repo(breed_risks: list[str] | None = None):
    repo = AsyncMock()
    repo.get_breed_risks = AsyncMock(return_value=breed_risks or [])
    repo.get_stop_foods = AsyncMock(return_value=[])
    return repo


@pytest.mark.asyncio
async def test_natural_distributes_calories_by_protein_weight():
    """Продукт с большим белком получает больше калорий."""
    lookups = {
        "курица": _make_lookup("курица", kcal=150.0, protein_g=25.0, fat_g=3.0, food_item_id=1),
        "гречка": _make_lookup("гречка", kcal=100.0, protein_g=3.0, fat_g=1.0, carb_g=20.0, food_item_id=2),
    }
    meal_svc = _make_meal_svc(lookups)
    nutrition_repo = _make_nutrition_repo()

    svc = RecommendService(meal_svc, nutrition_repo)
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(daily_calories=500.0),
        ingredients=["курица", "гречка"],
    )

    assert len(result.items) == 2
    chicken = next(i for i in result.items if i.name == "курица")
    buckwheat = next(i for i in result.items if i.name == "гречка")
    # курица имеет больше белка → должна получить больше калорий
    assert chicken.kcal > buckwheat.kcal


@pytest.mark.asyncio
async def test_natural_excludes_fatal_stop_list_items():
    """Продукт с уровнем stop 1 (fatal) исключается из рекомендации."""
    lookups = {
        "шоколад": _make_lookup("шоколад", kcal=500.0, protein_g=5.0, fat_g=30.0),
        "курица":  _make_lookup("курица",  kcal=150.0, protein_g=25.0, fat_g=3.0, food_item_id=1),
    }
    meal_svc = _make_meal_svc(lookups)
    # Шоколад в стоп-листе level=1
    meal_svc.check_stop_list = MagicMock(
        side_effect=lambda name, stops: (
            StopCheckResult(1, name, "теобромин", "тахикардия")
            if name == "шоколад"
            else StopCheckResult(None, None, None, None)
        )
    )
    nutrition_repo = _make_nutrition_repo()

    svc = RecommendService(meal_svc, nutrition_repo)
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(),
        ingredients=["шоколад", "курица"],
    )

    names = [i.name for i in result.items]
    assert "шоколад" not in names
    assert "курица" in names
    assert any("шоколад" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_natural_skips_not_found_ingredient():
    """Ингредиент, которого нет в БД и DeepSeek, пропускается без ошибки."""
    lookups = {
        "курица": _make_lookup("курица", kcal=150.0, protein_g=25.0, fat_g=3.0, food_item_id=1),
        "загадочный продукт": None,
    }
    meal_svc = _make_meal_svc(lookups)
    nutrition_repo = _make_nutrition_repo()

    svc = RecommendService(meal_svc, nutrition_repo)
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=_make_ration(),
        ingredients=["курица", "загадочный продукт"],
    )

    assert len(result.items) == 1
    assert result.items[0].name == "курица"


@pytest.mark.asyncio
async def test_commercial_calculates_daily_grams():
    """Суточные граммы = (daily_calories / kcal_per_100g) * 100."""
    lookups = {"Royal Canin Adult": _make_lookup(
        "Royal Canin Adult", kcal=360.0, protein_g=26.0, fat_g=16.0,
        carb_g=40.0, calcium_mg=1200.0, phosphorus_mg=950.0,
        omega3_mg=200.0, food_item_id=10,
    )}
    meal_svc = _make_meal_svc(lookups)
    nutrition_repo = _make_nutrition_repo()

    svc = RecommendService(meal_svc, nutrition_repo)
    result = await svc.recommend_commercial(
        pet=_make_pet(), ration=_make_ration(daily_calories=720.0),
        product_name="Royal Canin Adult",
    )

    assert len(result.items) == 1
    item = result.items[0]
    expected_grams = round((720.0 / 360.0) * 100, 1)
    assert abs(item.grams - expected_grams) < 1.0


@pytest.mark.asyncio
async def test_commercial_detects_taurine_deficiency_for_cat():
    """Для кошки с нехваткой таурина появляется дефицит."""
    lookups = {"Some Cat Food": _make_lookup(
        "Some Cat Food", kcal=350.0, protein_g=30.0, fat_g=12.0,
        carb_g=20.0, taurine_mg=0.0,  # таурин отсутствует
        calcium_mg=800.0, phosphorus_mg=700.0, omega3_mg=300.0,
        food_item_id=11,
    )}
    meal_svc = _make_meal_svc(lookups)
    meal_svc.get_required_micros = MagicMock(
        return_value=["taurine_mg", "omega3_mg", "calcium_mg", "phosphorus_mg"]
    )
    meal_svc.compute_micro_targets = MagicMock(return_value={
        "taurine_mg": 500.0, "omega3_mg": 400.0,
        "calcium_mg": 720.0, "phosphorus_mg": 640.0,
    })
    meal_svc.get_summary_tip = MagicMock(return_value="Не хватает таурина — обязателен для кошек")
    nutrition_repo = _make_nutrition_repo()

    svc = RecommendService(meal_svc, nutrition_repo)
    result = await svc.recommend_commercial(
        pet=_make_pet(species="cat"), ration=_make_ration(),
        product_name="Some Cat Food",
    )

    assert any("таурин" in d.lower() for d in result.deficiencies)


@pytest.mark.asyncio
async def test_covers_pct_reflects_calorie_coverage():
    """covers_pct отражает % покрытия суточной нормы калорий."""
    ration = _make_ration(daily_calories=1000.0)
    lookups = {"курица": _make_lookup("курица", kcal=200.0, protein_g=25.0, fat_g=3.0, food_item_id=1)}
    meal_svc = _make_meal_svc(lookups)
    nutrition_repo = _make_nutrition_repo()

    svc = RecommendService(meal_svc, nutrition_repo)
    result = await svc.recommend_natural(
        pet=_make_pet(), ration=ration, ingredients=["курица"],
    )

    # covers_pct = итоговые ккал / daily_calories * 100
    expected = round(result.totals.kcal / 1000.0 * 100, 1)
    assert abs(result.covers_pct - expected) < 1.0
```

- [ ] **Шаг 2: Запустить тесты — убедиться что FAIL**

```bash
python -m pytest tests/test_recommend_service.py -v
```

Ожидаем: `ImportError: cannot import name 'RecommendService'`

- [ ] **Шаг 3: Реализовать RecommendService**

```python
# app/services/recommend_service.py
from app.models.pet import Pet
from app.models.ration import Ration
from app.schemas.recommend import RecommendItem, RecommendResponse, NutrientMap
from app.services.meal_service import MealService
from app.repositories.nutrition_repo import NutritionRepository

_SUPPORTED_SPECIES = {"cat", "dog"}


class RecommendService:
    def __init__(self, meal_svc: MealService, nutrition_repo: NutritionRepository):
        self.meal_svc = meal_svc
        self.nutrition_repo = nutrition_repo

    async def recommend_natural(
        self, pet: Pet, ration: Ration, ingredients: list[str],
    ) -> RecommendResponse:
        breed_risks = await self.nutrition_repo.get_breed_risks(pet.breed or "")
        stop_foods = await self.nutrition_repo.get_stop_foods(pet.species, level=1)
        daily_calories = float(ration.daily_calories)

        lookups = {}
        warnings: list[str] = []

        for name in ingredients:
            result = await self.meal_svc.lookup_product(name)
            if result is None:
                warnings.append(f"Не удалось найти «{name}» — пропущен")
                continue
            stop = self.meal_svc.check_stop_list(name, stop_foods)
            if stop.level == 1:
                warnings.append(
                    f"⛔ «{stop.product_name}» нельзя — {stop.clinical_effect}. Исключён."
                )
                continue
            lookups[name] = result

        if not lookups:
            return RecommendResponse(
                items=[], totals=NutrientMap(), targets=NutrientMap(),
                micro_coverage={}, covers_pct=0.0,
                deficiencies=[], warnings=warnings,
            )

        # Distribute calories proportionally by protein content
        proteins = {n: max(lu.protein_g, 0.1) for n, lu in lookups.items()}
        total_protein = sum(proteins.values())

        items: list[RecommendItem] = []
        for name, lu in lookups.items():
            allocated_kcal = daily_calories * (proteins[name] / total_protein)
            grams = round((allocated_kcal / lu.kcal) * 100, 1) if lu.kcal > 0 else 0.0
            factor = grams / 100
            items.append(RecommendItem(
                name=lu.name,
                grams=grams,
                kcal=round(lu.kcal * factor, 1),
                protein_g=round(lu.protein_g * factor, 1),
                fat_g=round(lu.fat_g * factor, 1),
                carb_g=round(lu.carb_g * factor, 1),
                calcium_mg=round(lu.calcium_mg * factor, 1),
                phosphorus_mg=round(lu.phosphorus_mg * factor, 1),
                omega3_mg=round(lu.omega3_mg * factor, 1),
                taurine_mg=round(lu.taurine_mg * factor, 1),
                food_item_id=lu.food_item_id,
            ))

        return self._build_response(items, pet, ration, breed_risks, warnings)

    async def recommend_commercial(
        self, pet: Pet, ration: Ration, product_name: str,
    ) -> RecommendResponse:
        breed_risks = await self.nutrition_repo.get_breed_risks(pet.breed or "")
        daily_calories = float(ration.daily_calories)

        lu = await self.meal_svc.lookup_product(product_name)
        if lu is None:
            return RecommendResponse(
                items=[], totals=NutrientMap(), targets=NutrientMap(),
                micro_coverage={}, covers_pct=0.0,
                deficiencies=[],
                warnings=[f"Не удалось найти «{product_name}». Попробуй другое название."],
            )

        grams = round((daily_calories / lu.kcal) * 100, 1) if lu.kcal > 0 else 0.0
        factor = grams / 100
        items = [RecommendItem(
            name=lu.name,
            grams=grams,
            kcal=round(lu.kcal * factor, 1),
            protein_g=round(lu.protein_g * factor, 1),
            fat_g=round(lu.fat_g * factor, 1),
            carb_g=round(lu.carb_g * factor, 1),
            calcium_mg=round(lu.calcium_mg * factor, 1),
            phosphorus_mg=round(lu.phosphorus_mg * factor, 1),
            omega3_mg=round(lu.omega3_mg * factor, 1),
            taurine_mg=round(lu.taurine_mg * factor, 1),
            food_item_id=lu.food_item_id,
        )]

        return self._build_response(items, pet, ration, breed_risks, [])

    def _build_response(
        self, items: list[RecommendItem], pet: Pet, ration: Ration,
        breed_risks: list[str], warnings: list[str],
    ) -> RecommendResponse:
        daily_calories = float(ration.daily_calories)

        totals_dict = {
            "kcal": sum(i.kcal for i in items),
            "protein_g": sum(i.protein_g for i in items),
            "fat_g": sum(i.fat_g for i in items),
            "carb_g": sum(i.carb_g for i in items),
            "calcium_mg": sum(i.calcium_mg for i in items),
            "phosphorus_mg": sum(i.phosphorus_mg for i in items),
            "omega3_mg": sum(i.omega3_mg for i in items),
            "taurine_mg": sum(i.taurine_mg for i in items),
        }
        totals = NutrientMap(**{k: round(v, 1) for k, v in totals_dict.items()})
        covers_pct = round(totals_dict["kcal"] / daily_calories * 100, 1) if daily_calories > 0 else 0.0

        # Micro targets and coverage (only for supported species)
        micro_coverage: dict[str, float] = {}
        deficiencies: list[str] = []
        targets = NutrientMap()

        if pet.species in _SUPPORTED_SPECIES:
            required_micros = self.meal_svc.get_required_micros(pet.species, breed_risks)
            micro_targets = self.meal_svc.compute_micro_targets(
                mer=daily_calories,
                meals_per_day=1,
                species=pet.species,
                required_micros=required_micros,
            )
            daily_grams_est = daily_calories / 350 * 100
            pct_prot = 0.225 if pet.age_months < 12 else 0.18
            fat_pct_kcal = 0.25 if pet.age_months < 12 else 0.20
            full_targets = {
                "kcal": daily_calories,
                "protein_g": round(daily_grams_est * pct_prot, 1),
                "fat_g": round(daily_calories * fat_pct_kcal / 9, 1),
                **micro_targets,
            }
            targets = NutrientMap(**{
                k: round(v, 1) for k, v in full_targets.items()
                if k in NutrientMap.model_fields
            })
            for micro, tval in micro_targets.items():
                got = totals_dict.get(micro, 0)
                micro_coverage[micro] = round(got / tval * 100, 1) if tval > 0 else 0.0

            tip = self.meal_svc.get_summary_tip(totals_dict, full_targets, required_micros)
            if tip:
                deficiencies.append(tip)

            excess = self.meal_svc.get_excess_warnings(
                totals=totals_dict,
                target_kcal=daily_calories,
                species=pet.species,
                age_months=pet.age_months,
                weight_kg=float(pet.weight_kg),
            )
            warnings.extend(excess)

            # Ca:P ratio warning
            ca = totals_dict.get("calcium_mg", 0)
            p = totals_dict.get("phosphorus_mg", 0)
            if p > 0 and (ca / p) < 1.2:
                warnings.append(f"⚠️ Ca:P = {ca/p:.2f}:1 — ниже нормы 1.2:1")

        return RecommendResponse(
            items=items,
            totals=totals,
            targets=targets,
            micro_coverage=micro_coverage,
            covers_pct=covers_pct,
            deficiencies=deficiencies,
            warnings=warnings,
        )
```

- [ ] **Шаг 4: Запустить тесты — убедиться что PASS**

```bash
python -m pytest tests/test_recommend_service.py -v
```

Ожидаем: все 6 тестов зелёные.

- [ ] **Шаг 5: Коммит**

```bash
git add app/services/recommend_service.py tests/test_recommend_service.py
git commit -m "feat: add RecommendService with natural and commercial modes"
```

---

## Task 4: Новые endpoint в meal router

**Files:**
- Modify: `app/routers/meal.py`

- [ ] **Шаг 1: Добавить импорты в начало meal.py**

В `app/routers/meal.py` добавить к существующим импортам:

```python
from app.schemas.recommend import RecommendRequest, RecommendResponse, DailyAddNamedRequest
from app.repositories.nutrition_repo import NutritionRepository
from app.services.recommend_service import RecommendService
```

- [ ] **Шаг 2: Добавить endpoint POST /recommend в конец файла**

```python
@router.post("/recommend", response_model=RecommendResponse)
async def recommend_meal(
    body: RecommendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    telegram_id = request.state.telegram_id
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(
        pet_id=body.pet_id, owner_id=user.id
    )
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    ration = await NutritionRepository(db).get_ration_by_pet(body.pet_id)
    if ration is None:
        raise HTTPException(status_code=400, detail={"error": "no_ration"})

    repo = MealRepository(db)
    meal_svc = MealService(repo)
    nutrition_repo = NutritionRepository(db)
    svc = RecommendService(meal_svc, nutrition_repo)

    if body.mode == "natural":
        if not body.ingredients:
            raise HTTPException(status_code=400, detail={"error": "ingredients_required"})
        return await svc.recommend_natural(pet=pet, ration=ration, ingredients=body.ingredients)

    # commercial
    if not body.product_name.strip():
        raise HTTPException(status_code=400, detail={"error": "product_name_required"})
    return await svc.recommend_commercial(pet=pet, ration=ration, product_name=body.product_name)
```

- [ ] **Шаг 3: Добавить endpoint POST /daily/add-named в конец файла**

```python
@router.post("/daily/add-named")
async def daily_add_named(
    body: DailyAddNamedRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Добавить продукт в дневной лог по данным нутриентов (без food_item_id — для DeepSeek продуктов)."""
    if body.grams <= 0:
        raise HTTPException(status_code=400, detail={"error": "invalid_grams"})

    telegram_id = request.state.telegram_id
    today = str(_date.today())

    user = await UserService(UserRepository(db)).get_or_create(telegram_id=telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=body.pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    ration = await NutritionRepository(db).get_ration_by_pet(body.pet_id)
    if ration is None:
        raise HTTPException(status_code=400, detail={"error": "no_ration"})

    repo = MealRepository(db)
    svc = MealService(repo)
    breed_risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")

    session = await repo.get_daily_session(telegram_id, body.pet_id)
    if session and session.get("date") != today:
        await _save_daily_session(session, pet, ration, db)
        session = None

    if session is None:
        required_micros = svc.get_required_micros(pet.species, breed_risks)
        micro_targets = svc.compute_micro_targets(
            mer=float(ration.daily_calories), meals_per_day=1,
            species=pet.species, required_micros=required_micros,
        )
        daily_grams_est = float(ration.daily_calories) / 350 * 100
        pct_prot = 0.225 if pet.age_months < 12 else 0.18
        fat_pct_kcal = 0.25 if pet.age_months < 12 else 0.20
        session = {
            "date": today,
            "items": [],
            "daily_target": {
                "kcal": float(ration.daily_calories),
                "protein_g": round(daily_grams_est * pct_prot, 1),
                "fat_g": round(float(ration.daily_calories) * fat_pct_kcal / 9, 1),
                **micro_targets,
            },
        }

    factor = body.grams / 100
    item = {
        "food_item_id": None,
        "name": body.name,
        "grams": round(body.grams, 1),
        "kcal": round(body.kcal_per_100g * factor, 1),
        "protein_g": round(body.protein_g * factor, 1),
        "fat_g": round(body.fat_g * factor, 1),
        "carb_g": round(body.carb_g * factor, 1),
        "calcium_mg": round(body.calcium_mg * factor, 1),
        "phosphorus_mg": round(body.phosphorus_mg * factor, 1),
        "omega3_mg": round(body.omega3_mg * factor, 1),
        "taurine_mg": round(body.taurine_mg * factor, 1),
    }
    session["items"].append(item)
    await repo.save_daily_session(telegram_id, body.pet_id, session)

    totals = svc._sum_items(session["items"])
    score, quality, tips = svc.compute_quality(
        totals=totals, daily_target=session["daily_target"],
        pet_species=pet.species, breed_risks=breed_risks,
        age_months=pet.age_months, weight_kg=float(pet.weight_kg),
    )

    return {
        "status": "added",
        "item": item,
        "items": session["items"],
        "totals": totals,
        "daily_target": session["daily_target"],
        "quality_score": score,
        "quality_label": quality,
        "tips": tips,
    }
```

- [ ] **Шаг 4: Проверить что все существующие тесты проходят**

```bash
python -m pytest tests/ -v --tb=short
```

Ожидаем: все зелёные.

- [ ] **Шаг 5: Коммит**

```bash
git add app/routers/meal.py
git commit -m "feat: add /meal/recommend and /meal/daily/add-named endpoints"
```

---

## Task 5: Frontend — API клиент

**Files:**
- Create: `miniapp/src/api/recommend.ts`

- [ ] **Шаг 1: Создать файл**

```typescript
// miniapp/src/api/recommend.ts
import client from './client';
import { DailySummary } from './meal';

export interface RecommendItem {
  name: string;
  grams: number;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
  calcium_mg: number;
  phosphorus_mg: number;
  omega3_mg: number;
  taurine_mg: number;
  food_item_id: number | null;
}

export interface NutrientMap {
  kcal: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
  calcium_mg: number;
  phosphorus_mg: number;
  omega3_mg: number;
  taurine_mg: number;
}

export interface RecommendResult {
  items: RecommendItem[];
  totals: NutrientMap;
  targets: NutrientMap;
  micro_coverage: Record<string, number>;
  covers_pct: number;
  deficiencies: string[];
  warnings: string[];
}

export async function fetchRecommendation(
  petId: number,
  mode: 'natural' | 'commercial',
  ingredients: string[],
  productName: string,
): Promise<RecommendResult> {
  const { data } = await client.post('/v1/meal/recommend', {
    pet_id: petId,
    mode,
    ingredients,
    product_name: productName,
  });
  return data;
}

export async function addNamedProduct(
  petId: number,
  item: RecommendItem,
): Promise<DailySummary> {
  const { data } = await client.post('/v1/meal/daily/add-named', {
    pet_id: petId,
    name: item.name,
    grams: item.grams,
    kcal_per_100g: item.grams > 0 ? (item.kcal / item.grams) * 100 : 0,
    protein_g: item.grams > 0 ? (item.protein_g / item.grams) * 100 : 0,
    fat_g: item.grams > 0 ? (item.fat_g / item.grams) * 100 : 0,
    carb_g: item.grams > 0 ? (item.carb_g / item.grams) * 100 : 0,
    calcium_mg: item.grams > 0 ? (item.calcium_mg / item.grams) * 100 : 0,
    phosphorus_mg: item.grams > 0 ? (item.phosphorus_mg / item.grams) * 100 : 0,
    omega3_mg: item.grams > 0 ? (item.omega3_mg / item.grams) * 100 : 0,
    taurine_mg: item.grams > 0 ? (item.taurine_mg / item.grams) * 100 : 0,
  });
  return data;
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add miniapp/src/api/recommend.ts
git commit -m "feat: add recommend API client"
```

---

## Task 6: Frontend — useRecommend hook

**Files:**
- Create: `miniapp/src/hooks/useRecommend.ts`

- [ ] **Шаг 1: Создать файл**

```typescript
// miniapp/src/hooks/useRecommend.ts
import { useState, useCallback } from 'react';
import { addDailyProduct } from '../api/meal';
import { fetchRecommendation, addNamedProduct, RecommendResult, RecommendItem } from '../api/recommend';

const MODE_KEY = 'petfeed_feed_mode';
const RECENT_KEY = 'petfeed_recent_ingredients';
const MAX_RECENT = 7;

function loadMode(): 'natural' | 'commercial' {
  return (localStorage.getItem(MODE_KEY) as 'natural' | 'commercial') ?? 'natural';
}

function saveMode(mode: 'natural' | 'commercial'): void {
  localStorage.setItem(MODE_KEY, mode);
}

function loadRecentIngredients(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function saveRecentIngredients(names: string[]): void {
  localStorage.setItem(RECENT_KEY, JSON.stringify(names.slice(0, MAX_RECENT)));
}

export function useRecommend(petId: number | null, onApplied: () => void) {
  const [mode, setModeState] = useState<'natural' | 'commercial'>(loadMode);
  const [selected, setSelected] = useState<string[]>([]);
  const [productName, setProductName] = useState('');
  const [result, setResult] = useState<RecommendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recentIngredients = loadRecentIngredients();

  const setMode = useCallback((m: 'natural' | 'commercial') => {
    setModeState(m);
    saveMode(m);
    setResult(null);
    setSelected([]);
    setProductName('');
    setError(null);
  }, []);

  const toggleIngredient = useCallback((name: string) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
    setResult(null);
  }, []);

  const recommend = useCallback(async () => {
    if (!petId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecommendation(
        petId,
        mode,
        mode === 'natural' ? selected : [],
        mode === 'commercial' ? productName : '',
      );
      setResult(data);
    } catch {
      setError('Не удалось получить рекомендацию. Попробуй ещё раз.');
    } finally {
      setLoading(false);
    }
  }, [petId, mode, selected, productName]);

  const apply = useCallback(async () => {
    if (!petId || !result || applying) return;
    setApplying(true);
    try {
      for (const item of result.items) {
        if (item.food_item_id != null) {
          await addDailyProduct(petId, item.food_item_id, item.grams);
        } else {
          await addNamedProduct(petId, item);
        }
      }
      // Сохранить использованные ингредиенты в recent
      if (mode === 'natural') {
        const updated = Array.from(new Set([...selected, ...recentIngredients]));
        saveRecentIngredients(updated);
      }
      setResult(null);
      setSelected([]);
      setProductName('');
      onApplied();
    } catch {
      setError('Ошибка при добавлении продуктов.');
    } finally {
      setApplying(false);
    }
  }, [petId, result, applying, mode, selected, recentIngredients, onApplied]);

  return {
    mode, setMode,
    selected, toggleIngredient,
    productName, setProductName,
    recentIngredients,
    result, loading, applying, error,
    recommend, apply,
  };
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add miniapp/src/hooks/useRecommend.ts
git commit -m "feat: add useRecommend hook with natural/commercial modes"
```

---

## Task 7: Frontend — RecommendBar компонент

**Files:**
- Create: `miniapp/src/components/RecommendBar.tsx`

- [ ] **Шаг 1: Создать компонент**

```tsx
// miniapp/src/components/RecommendBar.tsx
import { useState } from 'react';
import { FoodSearchResult } from '../api/meal';
import { RecommendResult } from '../api/recommend';
import { c } from '../theme';

interface Props {
  mode: 'natural' | 'commercial';
  setMode: (m: 'natural' | 'commercial') => void;
  selected: string[];
  toggleIngredient: (name: string) => void;
  recentIngredients: string[];
  productName: string;
  setProductName: (v: string) => void;
  result: RecommendResult | null;
  loading: boolean;
  applying: boolean;
  error: string | null;
  recommend: () => void;
  apply: () => void;
  onSearchIngredient: (q: string) => void;
  searchResults: FoodSearchResult[];
}

export function RecommendBar({
  mode, setMode, selected, toggleIngredient,
  recentIngredients, productName, setProductName,
  result, loading, applying, error,
  recommend, apply,
  onSearchIngredient, searchResults,
}: Props) {
  const [showSearch, setShowSearch] = useState(false);
  const [ingredientQuery, setIngredientQuery] = useState('');

  const chipStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 16px',
    borderRadius: 20,
    border: `1px solid ${active ? c.accent : c.border}`,
    background: active ? c.accent : c.bg,
    color: active ? c.accentText : c.text,
    fontSize: 14,
    fontWeight: active ? 600 : 400,
    cursor: 'pointer',
  });

  const ingredientChip = (name: string): React.CSSProperties => ({
    padding: '6px 12px',
    borderRadius: 16,
    border: `1px solid ${selected.includes(name) ? c.accent : c.border}`,
    background: selected.includes(name) ? `${c.accent}22` : c.bgSecondary,
    color: c.text,
    fontSize: 13,
    cursor: 'pointer',
    flexShrink: 0,
  });

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button style={chipStyle(mode === 'natural')} onClick={() => setMode('natural')}>
          🥩 Натуральный
        </button>
        <button style={chipStyle(mode === 'commercial')} onClick={() => setMode('commercial')}>
          🛒 Готовый корм
        </button>
      </div>

      {/* Natural mode */}
      {mode === 'natural' && (
        <div>
          {recentIngredients.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              {recentIngredients.map((name) => (
                <button key={name} style={ingredientChip(name)} onClick={() => toggleIngredient(name)}>
                  {selected.includes(name) ? '✓ ' : ''}{name}
                </button>
              ))}
              <button
                style={{ ...ingredientChip(''), border: `1px dashed ${c.border}` }}
                onClick={() => setShowSearch(!showSearch)}
              >
                + Найти
              </button>
            </div>
          )}

          {(recentIngredients.length === 0 || showSearch) && (
            <div style={{ marginBottom: 10 }}>
              <input
                value={ingredientQuery}
                onChange={(e) => {
                  setIngredientQuery(e.target.value);
                  if (e.target.value.length >= 2) onSearchIngredient(e.target.value);
                }}
                placeholder="🔍 Добавить ингредиент..."
                style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: `1px solid ${c.border}`, fontSize: 14, background: c.bg, color: c.text, outline: 'none', boxSizing: 'border-box' }}
              />
              {searchResults.length > 0 && (
                <div style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 10, marginTop: 4, overflow: 'hidden' }}>
                  {searchResults.slice(0, 5).map((r) => (
                    <div
                      key={r.id}
                      onClick={() => {
                        toggleIngredient(r.name);
                        setIngredientQuery('');
                        setShowSearch(false);
                      }}
                      style={{ padding: '8px 12px', borderBottom: `1px solid ${c.border}`, cursor: 'pointer', fontSize: 13, color: c.text }}
                    >
                      {r.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {selected.length > 0 && (
            <div style={{ fontSize: 13, color: c.hint, marginBottom: 8 }}>
              Выбрано: {selected.join(', ')}
            </div>
          )}

          <button
            onClick={recommend}
            disabled={selected.length === 0 || loading}
            style={{ width: '100%', padding: '11px 0', background: c.accent, color: c.accentText, border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: selected.length === 0 || loading ? 'not-allowed' : 'pointer', opacity: selected.length === 0 || loading ? 0.5 : 1 }}
          >
            {loading ? 'Подбираем...' : '✨ Подобрать граммовку'}
          </button>
        </div>
      )}

      {/* Commercial mode */}
      {mode === 'commercial' && (
        <div>
          <input
            value={productName}
            onChange={(e) => {
              setProductName(e.target.value);
              if (e.target.value.length >= 2) onSearchIngredient(e.target.value);
            }}
            placeholder="🔍 Найди корм (Royal Canin, Purina...)"
            style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: `1px solid ${c.border}`, fontSize: 14, background: c.bg, color: c.text, outline: 'none', boxSizing: 'border-box', marginBottom: 8 }}
          />
          {searchResults.length > 0 && !result && (
            <div style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 10, marginBottom: 8, overflow: 'hidden' }}>
              {searchResults.slice(0, 5).map((r) => (
                <div
                  key={r.id}
                  onClick={() => setProductName(r.name)}
                  style={{ padding: '8px 12px', borderBottom: `1px solid ${c.border}`, cursor: 'pointer', fontSize: 13, color: c.text }}
                >
                  {r.name}
                </div>
              ))}
            </div>
          )}
          <button
            onClick={recommend}
            disabled={!productName.trim() || loading}
            style={{ width: '100%', padding: '11px 0', background: c.accent, color: c.accentText, border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: !productName.trim() || loading ? 'not-allowed' : 'pointer', opacity: !productName.trim() || loading ? 0.5 : 1 }}
          >
            {loading ? 'Ищем...' : '✨ Рассчитать граммовку'}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ marginTop: 8, color: c.destructive, fontSize: 13 }}>{error}</div>
      )}

      {/* Result */}
      {result && (
        <div style={{ marginTop: 12, background: c.bgSecondary, borderRadius: 14, padding: 14 }}>
          <div style={{ fontWeight: 600, fontSize: 15, color: c.text, marginBottom: 8 }}>
            Рекомендация · покрытие {result.covers_pct}%
          </div>

          {result.items.map((item, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 6, marginBottom: 6, borderBottom: `1px solid ${c.border}` }}>
              <div>
                <div style={{ fontSize: 14, color: c.text, fontWeight: 500 }}>{item.name}</div>
                <div style={{ fontSize: 12, color: c.hint, marginTop: 2 }}>
                  {item.grams}г · {Math.round(item.kcal)} ккал · Б:{Math.round(item.protein_g)}г Ж:{Math.round(item.fat_g)}г
                </div>
              </div>
            </div>
          ))}

          {result.deficiencies.map((d, i) => (
            <div key={i} style={{ fontSize: 12, color: '#ff9500', marginTop: 4 }}>💊 {d}</div>
          ))}

          {result.warnings.map((w, i) => (
            <div key={i} style={{ fontSize: 12, color: c.destructive, marginTop: 4 }}>{w}</div>
          ))}

          <button
            onClick={apply}
            disabled={applying}
            style={{ width: '100%', marginTop: 12, padding: '11px 0', background: '#34c759', color: '#fff', border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: applying ? 'not-allowed' : 'pointer', opacity: applying ? 0.6 : 1 }}
          >
            {applying ? 'Добавляем...' : '✅ Применить к дню'}
          </button>

          <button
            onClick={() => { setResult && (result as any); }}
            style={{ width: '100%', marginTop: 6, padding: '8px 0', background: 'none', border: 'none', color: c.hint, fontSize: 13, cursor: 'pointer' }}
            onClick={() => window.location.reload()}
          >
            Отмена
          </button>
        </div>
      )}
    </div>
  );
}
```

> ⚠️ Замени двойной `onClick` у кнопки "Отмена" в шаге выше на корректную логику сброса результата через хук (убери `window.location.reload()`):

```tsx
// Правильная кнопка Отмена — используй setResult(null) через колбэк
// В RecommendBar добавь проп:  onCancel: () => void
// И в useRecommend добавь:  const cancel = useCallback(() => setResult(null), []);
```

- [ ] **Шаг 2: Исправить кнопку Отмена — добавить onCancel проп**

В `RecommendBar.tsx`:
```tsx
// Добавить в Props:
onCancel: () => void;

// Заменить кнопку Отмена на:
<button
  onClick={onCancel}
  style={{ width: '100%', marginTop: 6, padding: '8px 0', background: 'none', border: 'none', color: c.hint, fontSize: 13, cursor: 'pointer' }}
>
  Отмена
</button>
```

В `useRecommend.ts` добавить:
```typescript
const cancel = useCallback(() => setResult(null), []);
// и вернуть из хука:
return { ..., cancel };
```

- [ ] **Шаг 3: Проверить TypeScript**

```bash
cd miniapp && npx tsc --noEmit
```

Ожидаем: 0 ошибок.

- [ ] **Шаг 4: Коммит**

```bash
git add miniapp/src/components/RecommendBar.tsx miniapp/src/hooks/useRecommend.ts
git commit -m "feat: add RecommendBar component and useRecommend hook"
```

---

## Task 8: Интеграция в Meal.tsx

**Files:**
- Modify: `miniapp/src/pages/Meal.tsx`

- [ ] **Шаг 1: Добавить импорты**

В начало `Meal.tsx` добавить:

```tsx
import { RecommendBar } from '../components/RecommendBar';
import { useRecommend } from '../hooks/useRecommend';
```

- [ ] **Шаг 2: Инициализировать хук внутри компонента Meal**

После строки с `useMealSession`:

```tsx
const { summary, history, searchResults, loading, searching, adding, search, add, undo, reset, loadSummary } =
    useMealSession(activePet?.id ?? null, activePet?.species ?? null);

const {
  mode, setMode,
  selected, toggleIngredient,
  recentIngredients,
  productName, setProductName,
  result: recommendResult,
  loading: recommending,
  applying,
  error: recommendError,
  recommend,
  apply,
  cancel,
} = useRecommend(activePet?.id ?? null, () => loadSummary());
```

> Примечание: `useMealSession` нужно экспортировать `loadSummary` — добавь его в return хука `useMealSession.ts`: `return { ..., loadSummary };`

- [ ] **Шаг 3: Добавить loadSummary в useMealSession возвращаемый объект**

В `miniapp/src/hooks/useMealSession.ts` строка 77:
```typescript
return { summary, history, searchResults, loading, searching, adding, search, add, undo, reset, loadSummary };
```

- [ ] **Шаг 4: Вставить RecommendBar в JSX перед блоком поиска**

В `Meal.tsx` найди `{/* Search */}` и вставь `RecommendBar` перед ним:

```tsx
{/* Recommendation */}
<RecommendBar
  mode={mode}
  setMode={setMode}
  selected={selected}
  toggleIngredient={toggleIngredient}
  recentIngredients={recentIngredients}
  productName={productName}
  setProductName={setProductName}
  result={recommendResult}
  loading={recommending}
  applying={applying}
  error={recommendError}
  recommend={recommend}
  apply={apply}
  onCancel={cancel}
  onSearchIngredient={search}
  searchResults={searchResults}
/>

{/* Search */}
```

- [ ] **Шаг 5: Проверить TypeScript**

```bash
cd miniapp && npx tsc --noEmit
```

Ожидаем: 0 ошибок.

- [ ] **Шаг 6: Запустить все Python тесты**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet && python -m pytest tests/ -v
```

Ожидаем: все зелёные.

- [ ] **Шаг 7: Финальный коммит**

```bash
git add miniapp/src/pages/Meal.tsx miniapp/src/hooks/useMealSession.ts
git commit -m "feat: integrate RecommendBar into Meal page"
```

---

## Checklist финального smoke-теста

После деплоя на Railway проверить вручную:

- [ ] Meal страница открывается, видны два чипса "🥩 Натуральный" / "🛒 Готовый корм"
- [ ] Натуральный: выбрать "курица" + "гречка" → нажать "Подобрать граммовку" → видны граммы и ккал
- [ ] Натуральный: нажать "Применить" → продукты появились в "Добавлено сегодня"
- [ ] Готовый корм: ввести "Royal Canin" → нажать "Рассчитать граммовку" → видна суточная граммовка
- [ ] Для кошки с нехваткой таурина → в блоке дефицитов появляется 💊 подсказка
- [ ] При вводе ингредиента через поиск → он появляется в чипсах при следующем открытии
- [ ] Переключение режима сохраняется после перезагрузки страницы (localStorage)
