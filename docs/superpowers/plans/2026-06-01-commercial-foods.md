# Commercial Foods Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a curated DB of ~30–50 commercial pet foods that feeds the meal-builder lookup, the AI assistant context, and a new bot food-picker screen, all gated behind the `feature_food_catalog` flag.

**Architecture:** New `commercial_foods` SQLAlchemy model + curated seed. A repository/service pair handles search, filtering, and pet→filter mapping. `MealService.lookup_product` consults `commercial_foods` before the DeepSeek fallback; `AiService.ask` injects matching foods into the prompt; a new bot handler + API endpoint expose the picker. A new generic `feature_flag_service.is_enabled` helper (Redis-cached, TTL 60s) gates the feature — this is the first in-code flag enforcement in the project.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (async), aiogram 3, Redis, rapidfuzz, pytest/pytest-asyncio.

---

## File Structure

**Create:**
- `app/models/commercial_food.py` — `CommercialFood` ORM model.
- `app/repositories/commercial_food_repo.py` — `CommercialFoodRepository` (CRUD/search/filter).
- `app/services/commercial_food_service.py` — `CommercialFoodService` (pet→filters, ranking, fuzzy lookup).
- `app/services/feature_flag_service.py` — generic `is_enabled(key, db)` helper, Redis-cached.
- `app/seeds/commercial_foods_seed.py` — curated ~30–50 foods + flag-row seeding.
- `app/routers/commercial_foods.py` — `GET /v1/commercial-foods`.
- `bot/handlers/food_picker.py` — bot picker flow.
- `tests/test_commercial_food_service.py`, `tests/test_feature_flag_service.py`, `tests/test_commercial_foods_router.py`.

**Modify:**
- `app/models/__init__.py` — register `CommercialFood`.
- `app/services/meal_service.py` — `lookup_product` consults commercial foods.
- `app/services/ai_service.py` — inject commercial-food context.
- `app/routers/ai.py` — pass commercial-food candidates to `ask`.
- `app/main.py:51` area — `include_router(commercial_foods.router, prefix="/v1")`.
- `bot/main.py:32` area — `dp.include_router(food_picker.router)`.
- `bot/states.py` — add `FoodPicker` states.
- `bot/keyboards.py` — picker keyboards + menu button.

---

## Task 1: CommercialFood model

**Files:**
- Create: `app/models/commercial_food.py`
- Modify: `app/models/__init__.py`
- Test: `tests/test_models.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models.py`:

```python
def test_commercial_food_model_columns():
    from app.models.commercial_food import CommercialFood
    cols = CommercialFood.__table__.columns.keys()
    for c in ["id", "brand", "name", "name_aliases", "species", "food_type",
              "life_stage", "breed_size", "condition_tags", "kcal_per_100g",
              "protein_g", "fat_g", "carb_g", "calcium_mg", "phosphorus_mg",
              "omega3_mg", "taurine_mg", "source", "barcode"]:
        assert c in cols
    assert CommercialFood.__tablename__ == "commercial_foods"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_commercial_food_model_columns -v`
Expected: FAIL with `ModuleNotFoundError: app.models.commercial_food`

- [ ] **Step 3: Write the model**

Create `app/models/commercial_food.py` (mirror `app/models/food_item.py` conventions):

```python
from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommercialFood(Base):
    __tablename__ = "commercial_foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    species: Mapped[str] = mapped_column(String(20), nullable=False)
    food_type: Mapped[str] = mapped_column(String(20), nullable=False)  # dry|wet
    life_stage: Mapped[str] = mapped_column(String(20), server_default="all")  # junior|adult|senior|all
    breed_size: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mini|medium|large|all
    condition_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    kcal_per_100g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    protein_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fat_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    carb_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    calcium_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    phosphorus_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    omega3_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    taurine_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(40), server_default="manufacturer")
    barcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

In `app/models/__init__.py` add the import next to the other model imports:

```python
from app.models.commercial_food import CommercialFood
```

and add `"CommercialFood"` to the `__all__` list.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_commercial_food_model_columns -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models/commercial_food.py app/models/__init__.py tests/test_models.py
git commit -m "feat: add CommercialFood model"
```

---

## Task 2: feature_flag_service.is_enabled helper

**Files:**
- Create: `app/services/feature_flag_service.py`
- Test: `tests/test_feature_flag_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_feature_flag_service.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.feature_flag_service import is_enabled


def _db_returning(flag):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = flag
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_cache_hit_skips_db():
    redis = AsyncMock()
    redis.get.return_value = "1"
    db = AsyncMock()
    with patch("app.services.feature_flag_service.get_redis", return_value=redis):
        assert await is_enabled("feature_food_catalog", db) is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_missing_flag_defaults_true():
    redis = AsyncMock()
    redis.get.return_value = None
    db = _db_returning(None)
    with patch("app.services.feature_flag_service.get_redis", return_value=redis):
        assert await is_enabled("feature_food_catalog", db) is True


@pytest.mark.asyncio
async def test_disabled_flag_from_db():
    redis = AsyncMock()
    redis.get.return_value = None
    flag = MagicMock(); flag.is_enabled = False
    db = _db_returning(flag)
    with patch("app.services.feature_flag_service.get_redis", return_value=redis):
        assert await is_enabled("feature_food_catalog", db) is False
    redis.set.assert_awaited()  # result cached
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_feature_flag_service.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.feature_flag_service`

- [ ] **Step 3: Write the helper**

Create `app/services/feature_flag_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag
from app.redis_client import get_redis

FLAG_CACHE_TTL = 60  # seconds, per CLAUDE.md


def _cache_key(key: str) -> str:
    return f"flag:{key}"


async def is_enabled(key: str, db: AsyncSession, default: bool = True) -> bool:
    """Return flag state. Cached in Redis (TTL 60s). Missing flag → default."""
    redis = get_redis()
    cached = await redis.get(_cache_key(key))
    if cached is not None:
        return cached == "1"

    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    enabled = flag.is_enabled if flag is not None else default

    await redis.set(_cache_key(key), "1" if enabled else "0", ex=FLAG_CACHE_TTL)
    return enabled
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_feature_flag_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/feature_flag_service.py tests/test_feature_flag_service.py
git commit -m "feat: add feature_flag_service.is_enabled helper with Redis cache"
```

---

## Task 3: CommercialFoodRepository

**Files:**
- Create: `app/repositories/commercial_food_repo.py`
- Test: `tests/test_commercial_foods_router.py` (repo-level integration test; uses `db_session` fixture)

- [ ] **Step 1: Write the failing test**

Create `tests/test_commercial_foods_router.py`:

```python
import json

import pytest

from app.models.commercial_food import CommercialFood
from app.repositories.commercial_food_repo import CommercialFoodRepository


async def _add(db, **kw):
    defaults = dict(
        brand="Royal Canin", name="Sterilised 37", name_aliases=json.dumps(["sterilised"]),
        species="cat", food_type="dry", life_stage="adult", breed_size=None,
        condition_tags=json.dumps(["sterilised"]), kcal_per_100g=350,
        protein_g=37, fat_g=12, carb_g=30, source="manufacturer",
    )
    defaults.update(kw)
    cf = CommercialFood(**defaults)
    db.add(cf)
    await db.commit()
    return cf


@pytest.mark.asyncio
async def test_search_matches_alias_and_species(db_session):
    await _add(db_session, species="cat")
    await _add(db_session, brand="Pro Plan", name="Adult Dog", species="dog",
               name_aliases=json.dumps(["pro plan"]), condition_tags=json.dumps([]))
    repo = CommercialFoodRepository(db_session)
    hits = await repo.search("sterilised", "cat")
    assert len(hits) == 1
    assert hits[0].brand == "Royal Canin"


@pytest.mark.asyncio
async def test_filter_by_food_type(db_session):
    await _add(db_session, food_type="dry")
    await _add(db_session, name="Wet Cat", food_type="wet", name_aliases=json.dumps([]))
    repo = CommercialFoodRepository(db_session)
    dry = await repo.filter(species="cat", food_type="dry")
    assert len(dry) == 1
    assert dry[0].food_type == "dry"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_commercial_foods_router.py -v`
Expected: FAIL with `ModuleNotFoundError: app.repositories.commercial_food_repo`

(If no test Postgres is available, these DB-backed tests are skipped/errored at collection for the `db_session` fixture — note for executor: run `docker compose up -d db` or point `TEST_DB_URL` to a live Postgres first.)

- [ ] **Step 3: Write the repository**

Create `app/repositories/commercial_food_repo.py`:

```python
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_food import CommercialFood


class CommercialFoodRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[CommercialFood]:
        result = await self.session.execute(select(CommercialFood))
        return list(result.scalars().all())

    async def get_by_id(self, food_id: int) -> CommercialFood | None:
        result = await self.session.execute(
            select(CommercialFood).where(CommercialFood.id == food_id)
        )
        return result.scalar_one_or_none()

    async def search(self, q: str, species: str, limit: int = 10) -> list[CommercialFood]:
        ql = q.lower()
        result = await self.session.execute(
            select(CommercialFood)
            .where(
                CommercialFood.species.in_([species, "all"]),
                or_(
                    func.lower(CommercialFood.name).contains(ql),
                    func.lower(CommercialFood.name_aliases).contains(ql),
                    func.lower(CommercialFood.brand).contains(ql),
                ),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def filter(
        self,
        species: str,
        food_type: str | None = None,
        life_stage: str | None = None,
        breed_size: str | None = None,
        tag: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CommercialFood]:
        stmt = select(CommercialFood).where(
            CommercialFood.species.in_([species, "all"])
        )
        if food_type:
            stmt = stmt.where(CommercialFood.food_type == food_type)
        if life_stage:
            stmt = stmt.where(CommercialFood.life_stage.in_([life_stage, "all"]))
        if breed_size:
            stmt = stmt.where(
                or_(CommercialFood.breed_size == breed_size,
                    CommercialFood.breed_size == "all",
                    CommercialFood.breed_size.is_(None))
            )
        if tag:
            stmt = stmt.where(func.lower(CommercialFood.condition_tags).contains(tag.lower()))
        stmt = stmt.order_by(CommercialFood.brand, CommercialFood.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_commercial_foods_router.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/repositories/commercial_food_repo.py tests/test_commercial_foods_router.py
git commit -m "feat: add CommercialFoodRepository with search and filter"
```

---

## Task 4: CommercialFoodService (pet→filters, ranking, fuzzy lookup)

**Files:**
- Create: `app/services/commercial_food_service.py`
- Test: `tests/test_commercial_food_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_commercial_food_service.py`:

```python
import json
from unittest.mock import MagicMock

import pytest

from app.models.commercial_food import CommercialFood
from app.services.commercial_food_service import CommercialFoodService


def make_cf(brand, name, species="cat", food_type="dry", life_stage="adult",
            breed_size=None, tags=None, kcal=350, prot=37, fat=12, carb=30):
    cf = CommercialFood()
    cf.brand = brand; cf.name = name; cf.name_aliases = json.dumps([name.lower()])
    cf.species = species; cf.food_type = food_type; cf.life_stage = life_stage
    cf.breed_size = breed_size; cf.condition_tags = json.dumps(tags or [])
    cf.kcal_per_100g = kcal; cf.protein_g = prot; cf.fat_g = fat; cf.carb_g = carb
    return cf


def make_pet(species="cat", age_months=36, breed="", goal="maintain"):
    pet = MagicMock()
    pet.species = species; pet.age_months = age_months; pet.breed = breed; pet.goal = goal
    return pet


def test_life_stage_from_age_cat():
    svc = CommercialFoodService(repo=MagicMock())
    assert svc.life_stage_for(make_pet(species="cat", age_months=6)) == "junior"
    assert svc.life_stage_for(make_pet(species="cat", age_months=36)) == "adult"
    assert svc.life_stage_for(make_pet(species="cat", age_months=132)) == "senior"


def test_pet_to_filters_maps_goal_and_risks():
    svc = CommercialFoodService(repo=MagicMock())
    pet = make_pet(species="cat", age_months=36, goal="lose")
    f = svc.pet_to_filters(pet, breed_risks=["urinary"])
    assert f["species"] == "cat"
    assert f["life_stage"] == "adult"
    assert "weight_control" in f["tags"]
    assert "urinary" in f["tags"]


def test_rank_prefers_more_matching_axes():
    svc = CommercialFoodService(repo=MagicMock())
    a = make_cf("A", "match-all", life_stage="adult", tags=["weight_control"])
    b = make_cf("B", "partial", life_stage="all", tags=[])
    filters = {"species": "cat", "life_stage": "adult", "food_type": "dry",
               "breed_size": None, "tags": ["weight_control"]}
    ranked = svc.rank([b, a], filters)
    assert ranked[0].brand == "A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_commercial_food_service.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.commercial_food_service`

- [ ] **Step 3: Write the service**

Create `app/services/commercial_food_service.py`:

```python
import json

from rapidfuzz import fuzz
from rapidfuzz import process as fuzz_process

from app.models.commercial_food import CommercialFood
from app.repositories.commercial_food_repo import CommercialFoodRepository

# Age thresholds (months): below junior_max → junior; above senior_min → senior.
LIFE_STAGE_THRESHOLDS = {
    "cat": (12, 120),
    "dog": (12, 96),
}
GOAL_TAGS = {"lose": "weight_control", "gain": "weight_gain"}


class CommercialFoodService:
    def __init__(self, repo: CommercialFoodRepository):
        self.repo = repo

    def life_stage_for(self, pet) -> str:
        junior_max, senior_min = LIFE_STAGE_THRESHOLDS.get(pet.species, (12, 120))
        if pet.age_months < junior_max:
            return "junior"
        if pet.age_months >= senior_min:
            return "senior"
        return "adult"

    def pet_to_filters(self, pet, breed_risks: list[str]) -> dict:
        tags: list[str] = []
        goal = getattr(pet, "goal", None)
        if goal in GOAL_TAGS:
            tags.append(GOAL_TAGS[goal])
        for risk in breed_risks:
            if risk in ("urinary", "renal", "sensitive", "obesity"):
                tags.append("weight_control" if risk == "obesity" else risk)
        return {
            "species": pet.species,
            "life_stage": self.life_stage_for(pet),
            "food_type": None,
            "breed_size": None,
            "tags": list(dict.fromkeys(tags)),  # dedup, keep order
        }

    def _axes_score(self, cf: CommercialFood, filters: dict) -> int:
        score = 0
        if filters.get("life_stage") and cf.life_stage in (filters["life_stage"], "all"):
            score += 1
        if filters.get("food_type") and cf.food_type == filters["food_type"]:
            score += 1
        if filters.get("breed_size") and cf.breed_size in (filters["breed_size"], "all", None):
            score += 1
        cf_tags = json.loads(cf.condition_tags or "[]")
        score += len(set(filters.get("tags", [])) & set(cf_tags))
        return score

    def rank(self, foods: list[CommercialFood], filters: dict) -> list[CommercialFood]:
        return sorted(foods, key=lambda cf: self._axes_score(cf, filters), reverse=True)

    async def find_for_lookup(self, product_name: str) -> CommercialFood | None:
        """Fuzzy match a free-text product name against name/aliases/brand."""
        foods = await self.repo.get_all()
        corpus: list[tuple[str, CommercialFood]] = []
        for cf in foods:
            corpus.append((f"{cf.brand} {cf.name}", cf))
            corpus.append((cf.name, cf))
            for alias in json.loads(cf.name_aliases or "[]"):
                corpus.append((alias, cf))
        if not corpus:
            return None
        texts = [c[0] for c in corpus]
        match = fuzz_process.extractOne(
            product_name, texts, scorer=fuzz.WRatio, score_cutoff=80
        )
        if match is None:
            return None
        return corpus[texts.index(match[0])][1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_commercial_food_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/commercial_food_service.py tests/test_commercial_food_service.py
git commit -m "feat: add CommercialFoodService with pet-to-filter mapping and ranking"
```

---

## Task 5: Curated seed + feature flag row

**Files:**
- Create: `app/seeds/commercial_foods_seed.py`
- Test: `tests/test_commercial_food_service.py` (append a data-integrity test that imports the seed list)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_commercial_food_service.py`:

```python
def test_seed_macros_energy_balance():
    """Each seed row's macros must agree with declared kcal within 15% (Atwater)."""
    from app.seeds.commercial_foods_seed import FOODS
    assert len(FOODS) >= 30
    for row in FOODS:
        kcal = row["kcal_per_100g"]
        calc = row["protein_g"] * 4 + row["fat_g"] * 9 + row["carb_g"] * 4
        assert kcal > 0
        assert abs(calc - kcal) / kcal <= 0.15, f"{row['brand']} {row['name']}: {calc} vs {kcal}"


def test_seed_required_fields_and_vocab():
    from app.seeds.commercial_foods_seed import FOODS
    for row in FOODS:
        assert row["species"] in {"cat", "dog"}
        assert row["food_type"] in {"dry", "wet"}
        assert row["life_stage"] in {"junior", "adult", "senior", "all"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_commercial_food_service.py::test_seed_macros_energy_balance -v`
Expected: FAIL with `ModuleNotFoundError: app.seeds.commercial_foods_seed`

- [ ] **Step 3: Write the seed**

Create `app/seeds/commercial_foods_seed.py`. Provide a `FOODS: list[dict]` with **≥30** curated rows. Below are the first rows as a concrete template; the executor fills the list to 30–50 popular RU-market foods (cat/dog × dry/wet × life_stage × condition), each documented with a `# source:` comment. **Every row's macros must satisfy the 15% energy-balance test above** — verify before committing.

```python
"""Curated commercial pet foods for RU market. Run once after migration.
Macros are per 100 g as-fed, converted from guaranteed analysis + label ME.
carb_g (NFE) = 100 - protein - fat - fiber - moisture - ash.
Run: python -m app.seeds.commercial_foods_seed
"""
import asyncio
import json

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.commercial_food import CommercialFood
from app.models.feature_flag import FeatureFlag

# key fields: brand, name, aliases, species, food_type, life_stage, breed_size,
#             tags, kcal_per_100g, protein_g, fat_g, carb_g, ca, p, omega3, taurine
FOODS: list[dict] = [
    # source: royalcanin.ru — Sterilised 37 (dry, cat, adult)
    {"brand": "Royal Canin", "name": "Sterilised 37",
     "aliases": ["sterilised", "стерилайзд"], "species": "cat", "food_type": "dry",
     "life_stage": "adult", "breed_size": None, "tags": ["sterilised", "weight_control"],
     "kcal_per_100g": 350, "protein_g": 37.0, "fat_g": 12.0, "carb_g": 31.0,
     "calcium_mg": 1100, "phosphorus_mg": 900, "omega3_mg": 600, "taurine_mg": 250},
    # source: ru.purina — Pro Plan Adult Dog Medium (dry, dog, adult, medium)
    {"brand": "Pro Plan", "name": "Adult Medium",
     "aliases": ["pro plan adult", "проплан"], "species": "dog", "food_type": "dry",
     "life_stage": "adult", "breed_size": "medium", "tags": [],
     "kcal_per_100g": 367, "protein_g": 26.0, "fat_g": 16.0, "carb_g": 40.0,
     "calcium_mg": 1000, "phosphorus_mg": 800, "omega3_mg": 300, "taurine_mg": 0},
    # ... executor: continue to >=30 rows (Hills, Acana, Grandorf, Brit, Monge,
    #     Farmina, Sheba/wet, etc.), covering junior & senior & wet types.
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # idempotent: skip rows that already exist (brand+name)
        existing = await session.execute(select(CommercialFood.brand, CommercialFood.name))
        seen = {(b, n) for b, n in existing.all()}
        added = 0
        for row in FOODS:
            if (row["brand"], row["name"]) in seen:
                continue
            session.add(CommercialFood(
                brand=row["brand"], name=row["name"],
                name_aliases=json.dumps(row["aliases"], ensure_ascii=False),
                species=row["species"], food_type=row["food_type"],
                life_stage=row["life_stage"], breed_size=row["breed_size"],
                condition_tags=json.dumps(row["tags"], ensure_ascii=False),
                kcal_per_100g=row["kcal_per_100g"], protein_g=row["protein_g"],
                fat_g=row["fat_g"], carb_g=row["carb_g"],
                calcium_mg=row.get("calcium_mg"), phosphorus_mg=row.get("phosphorus_mg"),
                omega3_mg=row.get("omega3_mg"), taurine_mg=row.get("taurine_mg"),
                source=row.get("source", "manufacturer"), barcode=row.get("barcode"),
            ))
            added += 1

        # feature flag row (idempotent)
        flag = (await session.execute(
            select(FeatureFlag).where(FeatureFlag.key == "feature_food_catalog")
        )).scalar_one_or_none()
        if flag is None:
            session.add(FeatureFlag(
                key="feature_food_catalog",
                name="Каталог коммерческих кормов",
                description="Подбор кормов в боте + данные для конструктора рациона и AI",
                is_enabled=True,
            ))

        await session.commit()
    print(f"Seeded {added} commercial foods (+ feature_food_catalog flag).")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_commercial_food_service.py -v`
Expected: PASS (all). If any row fails the 15% balance, fix that row's macros.

- [ ] **Step 5: Commit**

```bash
git add app/seeds/commercial_foods_seed.py tests/test_commercial_food_service.py
git commit -m "feat: add curated commercial foods seed + feature_food_catalog flag"
```

---

## Task 6: Meal-builder lookup consults commercial foods

**Files:**
- Modify: `app/services/meal_service.py` (`lookup_product`, ~line 184)
- Test: `tests/test_meal_service.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_meal_service.py`:

```python
@pytest.mark.asyncio
async def test_lookup_product_finds_commercial_before_deepseek():
    from app.models.commercial_food import CommercialFood
    repo = AsyncMock()
    repo.get_all_food_items.return_value = []  # not in food_items

    cf = CommercialFood()
    cf.id = 7; cf.brand = "Royal Canin"; cf.name = "Sterilised 37"
    cf.name_aliases = json.dumps(["sterilised"]); cf.species = "cat"
    cf.food_type = "dry"; cf.kcal_per_100g = 350; cf.protein_g = 37
    cf.fat_g = 12; cf.carb_g = 31; cf.calcium_mg = 1100; cf.phosphorus_mg = 900
    cf.omega3_mg = 600; cf.taurine_mg = 250; cf.condition_tags = "[]"

    svc = MealService(repo)
    svc._deepseek_lookup = AsyncMock()  # must NOT be called

    from unittest.mock import AsyncMock as _AM
    cf_repo = _AM(); cf_repo.get_all.return_value = [cf]
    svc._commercial_repo = cf_repo  # injected lookup source

    res = await svc.lookup_product("Royal Canin Sterilised")
    assert res is not None
    assert res.source == "commercial_db"
    assert res.kcal == 350
    svc._deepseek_lookup.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_meal_service.py::test_lookup_product_finds_commercial_before_deepseek -v`
Expected: FAIL (no `_commercial_repo` handling; falls through to DeepSeek)

- [ ] **Step 3: Modify `lookup_product`**

In `app/services/meal_service.py`, add an optional commercial-foods source. Add to `MealService.__init__` after `self.repo = repo`:

```python
        self._commercial_repo = None  # set by caller when feature_food_catalog is ON
```

Replace the body of `lookup_product` (currently returns food_item match else DeepSeek) so the commercial-foods check runs between them:

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
                food_item_id=fi.id,
            )

        cf = await self._lookup_commercial(product_name)
        if cf:
            return cf

        return await self._deepseek_lookup(product_name)

    async def _lookup_commercial(self, product_name: str) -> "FoodLookupResult | None":
        if self._commercial_repo is None:
            return None
        from app.services.commercial_food_service import CommercialFoodService
        svc = CommercialFoodService(self._commercial_repo)
        cf = await svc.find_for_lookup(product_name)
        if cf is None:
            return None
        return FoodLookupResult(
            name=f"{cf.brand} {cf.name}", grams=0,
            kcal=float(cf.kcal_per_100g),
            protein_g=float(cf.protein_g),
            fat_g=float(cf.fat_g),
            carb_g=float(cf.carb_g),
            calcium_mg=float(cf.calcium_mg or 0),
            phosphorus_mg=float(cf.phosphorus_mg or 0),
            omega3_mg=float(cf.omega3_mg or 0),
            taurine_mg=float(cf.taurine_mg or 0),
            source="commercial_db",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_meal_service.py -v`
Expected: PASS (existing meal tests still green + new one)

- [ ] **Step 5: Wire the repo at the call site**

In `app/routers/meal.py`, find where `MealService(repo)` is built for the product-lookup endpoint (the handler that calls `lookup_product` / `_add_product`, around the food search/add flow). Immediately after constructing the service, gate and inject:

```python
    from app.services.feature_flag_service import is_enabled
    from app.repositories.commercial_food_repo import CommercialFoodRepository
    if await is_enabled("feature_food_catalog", db):
        svc._commercial_repo = CommercialFoodRepository(db)
```

(Executor: apply at each `MealService(...)` site that can call `lookup_product`. Grep: `grep -n "lookup_product\|MealService(" app/routers/meal.py`.)

- [ ] **Step 6: Commit**

```bash
git add app/services/meal_service.py app/routers/meal.py tests/test_meal_service.py
git commit -m "feat: meal-builder lookup consults commercial foods before DeepSeek"
```

---

## Task 7: AI assistant context injection

**Files:**
- Modify: `app/services/ai_service.py` (`ask`), `app/routers/ai.py`
- Test: `tests/test_ai_service.py` (create if absent)

- [ ] **Step 1: Write the failing test**

Create/append `tests/test_ai_service.py`:

```python
from unittest.mock import MagicMock

from app.services.ai_service import build_food_context


def make_cf(brand, name, kcal, life_stage="adult"):
    cf = MagicMock()
    cf.brand = brand; cf.name = name; cf.kcal_per_100g = kcal
    cf.life_stage = life_stage; cf.food_type = "dry"
    return cf


def test_build_food_context_compact():
    foods = [make_cf("Royal Canin", "Sterilised 37", 350),
             make_cf("Pro Plan", "Adult", 367)]
    ctx = build_food_context(foods)
    assert "Royal Canin Sterilised 37" in ctx
    assert "350" in ctx
    assert ctx.count("\n") <= 6  # stays compact


def test_build_food_context_empty():
    assert build_food_context([]) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_service.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_food_context'`

- [ ] **Step 3: Add context builder + use it**

In `app/services/ai_service.py`, add a module-level helper:

```python
def build_food_context(foods: list) -> str:
    """Compact list of candidate commercial foods for the AI prompt."""
    if not foods:
        return ""
    lines = [
        f"- {cf.brand} {cf.name} ({cf.food_type}, {cf.life_stage}): "
        f"{float(cf.kcal_per_100g):.0f} ккал/100г"
        for cf in foods[:5]
    ]
    return "Подходящие корма из базы:\n" + "\n".join(lines) + "\n"
```

Change `ask` to accept and embed candidates. Update the signature and the context assembly:

```python
    async def ask(self, user: User, pet: Pet | None, question: str,
                  foods: list | None = None) -> tuple[str, bool]:
```

and after building `context` from the pet block, append:

```python
            context += build_food_context(foods or [])
```

- [ ] **Step 4: Pass candidates from the router**

In `app/routers/ai.py`, after `pet` is resolved (around line 40) and before calling `ask`, gather candidates when the flag is on:

```python
    foods = []
    if pet is not None:
        from app.services.feature_flag_service import is_enabled
        if await is_enabled("feature_food_catalog", db):
            from app.repositories.commercial_food_repo import CommercialFoodRepository
            from app.repositories.nutrition_repo import NutritionRepository
            from app.services.commercial_food_service import CommercialFoodService
            cf_repo = CommercialFoodRepository(db)
            cf_svc = CommercialFoodService(cf_repo)
            risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")
            filt = cf_svc.pet_to_filters(pet, risks)
            foods = cf_svc.rank(
                await cf_repo.filter(species=filt["species"],
                                     life_stage=filt["life_stage"], limit=10),
                filt,
            )[:5]

    answer, cache_hit = await ai_service.ask(
        user=user, pet=pet, question=data.question, foods=foods,
    )
```

(Replace the existing `answer, cache_hit = await ai_service.ask(...)` line.)

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_ai_service.py tests/test_commercial_food_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/ai_service.py app/routers/ai.py tests/test_ai_service.py
git commit -m "feat: inject matching commercial foods into AI assistant context"
```

---

## Task 8: API endpoint GET /v1/commercial-foods

**Files:**
- Create: `app/routers/commercial_foods.py`
- Modify: `app/main.py` (include_router)
- Test: `tests/test_commercial_foods_router.py` (append endpoint test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_commercial_foods_router.py`:

```python
from app.services.commercial_food_service import CommercialFoodService


@pytest.mark.asyncio
async def test_service_filter_returns_only_species(db_session):
    await _add(db_session, species="cat")
    await _add(db_session, brand="Pro Plan", name="Dog Adult", species="dog",
               name_aliases=json.dumps([]), condition_tags=json.dumps([]))
    repo = CommercialFoodRepository(db_session)
    svc = CommercialFoodService(repo)
    rows = await repo.filter(species="cat")
    ranked = svc.rank(rows, {"species": "cat", "life_stage": "adult",
                             "food_type": None, "breed_size": None, "tags": []})
    assert all(cf.species == "cat" for cf in ranked)
    assert len(ranked) == 1
```

(Endpoint HTTP wiring is exercised manually in Task 10 verification; this test locks the service/repo contract the router depends on.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_commercial_foods_router.py::test_service_filter_returns_only_species -v`
Expected: PASS for the service contract (already implemented) — this guards Task 8's assumptions. If it fails, fix repo/service before writing the router.

- [ ] **Step 3: Write the router**

Create `app/routers/commercial_foods.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.commercial_food_repo import CommercialFoodRepository
from app.services.commercial_food_service import CommercialFoodService
from app.services.feature_flag_service import is_enabled

router = APIRouter(prefix="/commercial-foods", tags=["commercial-foods"])


def _serialize(cf) -> dict:
    import json
    return {
        "id": cf.id, "brand": cf.brand, "name": cf.name,
        "species": cf.species, "food_type": cf.food_type,
        "life_stage": cf.life_stage, "breed_size": cf.breed_size,
        "tags": json.loads(cf.condition_tags or "[]"),
        "kcal_per_100g": float(cf.kcal_per_100g),
        "protein_g": float(cf.protein_g), "fat_g": float(cf.fat_g),
        "carb_g": float(cf.carb_g),
    }


@router.get("")
async def list_foods(
    species: str,
    request: Request,
    food_type: str | None = None,
    life_stage: str | None = None,
    breed_size: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    if not await is_enabled("feature_food_catalog", db):
        raise HTTPException(status_code=403, detail={"error": "feature_disabled"})
    repo = CommercialFoodRepository(db)
    if q and len(q.strip()) >= 2:
        rows = await repo.search(q.strip(), species, limit=limit)
    else:
        rows = await repo.filter(species=species, food_type=food_type,
                                 life_stage=life_stage, breed_size=breed_size,
                                 tag=tag, limit=limit, offset=offset)
    return [_serialize(cf) for cf in rows]
```

In `app/main.py`, add the import alongside the other router imports and register it next to `meal.router`:

```python
app.include_router(commercial_foods.router, prefix="/v1")
```

(Add `commercial_foods` to the existing routers import statement at the top of `app/main.py`.)

- [ ] **Step 4: Run tests + import check**

Run: `pytest tests/test_commercial_foods_router.py -v && python -c "import app.main"`
Expected: tests PASS, import OK (router registered without error)

- [ ] **Step 5: Commit**

```bash
git add app/routers/commercial_foods.py app/main.py tests/test_commercial_foods_router.py
git commit -m "feat: add GET /v1/commercial-foods endpoint gated by feature flag"
```

---

## Task 9: Bot food-picker screen

**Files:**
- Modify: `bot/states.py`, `bot/keyboards.py`, `bot/main.py`
- Create: `bot/handlers/food_picker.py`
- Test: `tests/test_keyboards.py` (create/append — pure keyboard structure, no network)

- [ ] **Step 1: Write the failing test**

Create/append `tests/test_keyboards.py`:

```python
def test_food_picker_keyboards_exist_and_carry_pet_id():
    from bot.keyboards import food_picker_filters_keyboard, food_picker_list_keyboard
    kb = food_picker_filters_keyboard(pet_id=5)
    flat = [b for row in kb.inline_keyboard for b in row]
    assert any("fp_type:dry:5" in b.callback_data for b in flat)
    assert any("fp_type:wet:5" in b.callback_data for b in flat)

    items = [{"id": 1, "brand": "Royal Canin", "name": "Sterilised 37",
              "kcal_per_100g": 350}]
    lst = food_picker_list_keyboard(items, pet_id=5, offset=0)
    flat2 = [b for row in lst.inline_keyboard for b in row]
    assert any("fp_card:1:5" in b.callback_data for b in flat2)


def test_main_menu_has_food_picker_button():
    from bot.keyboards import main_menu_keyboard
    kb = main_menu_keyboard("Барсик")
    flat = [b for row in kb.inline_keyboard for b in row]
    assert any(b.callback_data == "menu:food_picker" for b in flat)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_keyboards.py -v`
Expected: FAIL with `ImportError: cannot import name 'food_picker_filters_keyboard'`

- [ ] **Step 3: Add states, keyboards, menu button**

In `bot/states.py` append:

```python
class FoodPicker(StatesGroup):
    browsing = State()
```

In `bot/keyboards.py` add:

```python
def food_picker_filters_keyboard(pet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍖 Сухой", callback_data=f"fp_type:dry:{pet_id}"),
         InlineKeyboardButton(text="🥫 Влажный", callback_data=f"fp_type:wet:{pet_id}")],
        [InlineKeyboardButton(text="Показать все", callback_data=f"fp_type:all:{pet_id}")],
        [InlineKeyboardButton(text="← Меню", callback_data="meal_to_menu")],
    ])


def food_picker_list_keyboard(items: list[dict], pet_id: int, offset: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{it['brand']} {it['name']} · {it['kcal_per_100g']:.0f} ккал",
            callback_data=f"fp_card:{it['id']}:{pet_id}")]
        for it in items
    ]
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="←", callback_data=f"fp_page:{offset-20}:{pet_id}"))
    if len(items) == 20:
        nav.append(InlineKeyboardButton(text="→", callback_data=f"fp_page:{offset+20}:{pet_id}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="← Меню", callback_data="meal_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

In `main_menu_keyboard` (around line 92), add a button row after "Заказать корм":

```python
        [InlineKeyboardButton(text="🔎 Подобрать корм", callback_data="menu:food_picker")],
```

- [ ] **Step 4: Run keyboard test**

Run: `pytest tests/test_keyboards.py -v`
Expected: PASS

- [ ] **Step 5: Write the handler**

Create `bot/handlers/food_picker.py` (mirror `meal_builder.py` httpx pattern):

```python
import json

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import settings
from bot.keyboards import food_picker_filters_keyboard, food_picker_list_keyboard
from bot.states import FoodPicker

router = Router()


async def _fetch(telegram_id: int, params: dict) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/commercial-foods",
            params=params,
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    return resp.json() if resp.status_code == 200 else []


@router.callback_query(F.data == "menu:food_picker")
async def open_picker(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pet_id = data.get("active_pet_id") or data.get("meal_pet_id")
    if not pet_id:
        await callback.answer("Сначала выбери питомца", show_alert=True)
        return
    await state.set_state(FoodPicker.browsing)
    await callback.message.edit_text(
        "🔎 <b>Подбор корма</b>\nВыбери тип корма:",
        parse_mode="HTML",
        reply_markup=food_picker_filters_keyboard(int(pet_id)),
    )


@router.callback_query(FoodPicker.browsing, F.data.startswith("fp_type:"))
async def pick_type(callback: CallbackQuery, state: FSMContext):
    _, food_type, pet_id = callback.data.split(":")
    await _show_list(callback, state, int(pet_id), food_type, offset=0)


@router.callback_query(FoodPicker.browsing, F.data.startswith("fp_page:"))
async def page(callback: CallbackQuery, state: FSMContext):
    _, offset, pet_id = callback.data.split(":")
    data = await state.get_data()
    await _show_list(callback, state, int(pet_id),
                     data.get("fp_type", "all"), offset=int(offset))


async def _show_list(callback, state, pet_id: int, food_type: str, offset: int):
    await state.update_data(fp_type=food_type)
    # species inferred server-side requires species param; fetch pet species via meal session check
    species = (await state.get_data()).get("active_pet_species", "cat")
    params = {"species": species, "limit": 20, "offset": offset}
    if food_type != "all":
        params["food_type"] = food_type
    items = await _fetch(callback.from_user.id, params)
    if not items:
        await callback.message.edit_text(
            "Ничего не нашлось 😿",
            reply_markup=food_picker_filters_keyboard(pet_id))
        return
    await callback.message.edit_text(
        f"Найдено кормов: <b>{len(items)}</b>. Выбери, чтобы открыть карточку:",
        parse_mode="HTML",
        reply_markup=food_picker_list_keyboard(items, pet_id, offset),
    )


@router.callback_query(FoodPicker.browsing, F.data.startswith("fp_card:"))
async def show_card(callback: CallbackQuery, state: FSMContext):
    _, food_id, pet_id = callback.data.split(":")
    data = await state.get_data()
    species = data.get("active_pet_species", "cat")
    items = await _fetch(callback.from_user.id, {"species": species, "limit": 100})
    cf = next((i for i in items if i["id"] == int(food_id)), None)
    if cf is None:
        await callback.answer("Корм не найден", show_alert=True)
        return
    tags = ", ".join(cf.get("tags", [])) or "—"
    await callback.message.edit_text(
        f"<b>{cf['brand']} {cf['name']}</b>\n"
        f"Тип: {cf['food_type']} · {cf['life_stage']}\n"
        f"Ккал/100г: {cf['kcal_per_100g']:.0f}\n"
        f"Белок {cf['protein_g']:.0f} / Жир {cf['fat_g']:.0f} / Угл {cf['carb_g']:.0f} г\n"
        f"Назначение: {tags}",
        parse_mode="HTML",
        reply_markup=food_picker_filters_keyboard(int(pet_id)),
    )
```

In `bot/main.py` after `dp.include_router(feedback.router)` add:

```python
    dp.include_router(food_picker.router)
```

and add `food_picker` to the handler imports at the top of `bot/main.py`.

- [ ] **Step 6: Run tests + import check**

Run: `pytest tests/test_keyboards.py -v && python -c "import bot.main"`
Expected: PASS, import OK

> Note on `active_pet_species`: if the bot's FSM does not already store it, the executor sets it wherever `active_pet_id`/`meal_pet_id` is set (e.g. in the pet-switch / start-meal handlers) via `await state.update_data(active_pet_species=<species>)`. Grep: `grep -rn "active_pet_id\|meal_pet_id" bot/handlers`. Default `"cat"` is a safe fallback only.

- [ ] **Step 7: Commit**

```bash
git add bot/states.py bot/keyboards.py bot/handlers/food_picker.py bot/main.py tests/test_keyboards.py
git commit -m "feat: add bot food-picker screen behind feature_food_catalog"
```

---

## Task 10: Run seed, full suite, manual smoke test

**Files:** none (verification)

- [ ] **Step 1: Run the full test suite**

Run: `pytest -q`
Expected: all tests pass (note: DB-backed tests need a live `petfeed_test` Postgres — start it first).

- [ ] **Step 2: Apply the seed against the dev DB**

Run: `python -m app.seeds.commercial_foods_seed`
Expected: `Seeded N commercial foods (+ feature_food_catalog flag).` Re-run once more; expected `Seeded 0 commercial foods` (idempotency holds).

- [ ] **Step 3: Smoke-test the endpoint**

With the API running, run:
`curl -s "http://localhost:8000/v1/commercial-foods?species=cat&food_type=dry" -H "X-Telegram-Id: <your_id>"`
Expected: JSON array of cat dry foods.

- [ ] **Step 4: Smoke-test the flag toggle**

Toggle `feature_food_catalog` OFF in `/admin/flags`, wait >60s (cache TTL), repeat the curl.
Expected: HTTP 403 `{"error":"feature_disabled"}`. Toggle back ON.

- [ ] **Step 5: Final commit (docs)**

Update `CLAUDE.md` feature-flag list to add `feature_food_catalog` (MVP ON) and the new `/commercial-foods` router row in the API table.

```bash
git add CLAUDE.md
git commit -m "docs: record feature_food_catalog flag and commercial-foods API"
```

---

## Self-Review Notes

- **Spec coverage:** model (T1), flag helper (T2), repo (T3), service/pet-mapping/ranking (T4), curated seed + conversion + flag row (T5), meal-builder integration (T6), AI context (T7), API endpoint (T8), bot picker screen (T9), verification + docs (T10). All eight spec sections + the flag-helper requirement are covered.
- **Type consistency:** `CommercialFood` columns identical across T1/T3/T4/T5/T6. Service methods `life_stage_for`, `pet_to_filters`, `rank`, `find_for_lookup` referenced consistently in T4/T6/T7/T8. `is_enabled(key, db)` signature identical in T2/T6/T7/T8. Callback-data scheme `fp_type:/fp_page:/fp_card:` consistent across keyboards (T9 step 3) and handlers (T9 step 5).
- **Known executor responsibilities (not placeholders, explicit handoffs):** fill the seed list to ≥30 rows passing the energy-balance test (T5); wire `_commercial_repo` at every `lookup_product` call site (T6 step 5); ensure `active_pet_species` is stored in FSM (T9 note).
