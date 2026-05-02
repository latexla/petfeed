# MealBuilder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать подбор порции на одно кормление: диалог с ботом, стоп-лист, КБЖУ + микронутриенты, рекомендации — плюс упрощение: убрать шаг 9 из создания питомца и граммовку из рациона.

**Architecture:** Новая таблица `food_items` (~70 USDA-продуктов), MealService с rapidfuzz-поиском и DeepSeek fallback, сессия в Redis, три API-эндпоинта, FSM-диалог `MealBuilder`. Параллельно: удаление `food_category_id` из Pet и шага 9 из FSM создания питомца.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, aiogram 3, PostgreSQL, Redis, Alembic, rapidfuzz, openai SDK (DeepSeek)

---

## Карта файлов

| Действие | Файл | Назначение |
|----------|------|------------|
| CREATE | `app/models/food_item.py` | Модель `food_items` |
| CREATE | `app/seeds/food_items_seed.py` | ~70 продуктов из USDA |
| CREATE | `app/repositories/meal_repo.py` | Запросы к food_items, Redis-сессия |
| CREATE | `app/services/meal_service.py` | Поиск, стоп-лист, расчёт, рекомендации |
| CREATE | `app/routers/meal.py` | POST add-product, GET summary, DELETE reset/undo |
| CREATE | `bot/handlers/meal_builder.py` | FSM-диалог MealBuilder |
| CREATE | `alembic/versions/a1b2c3_meal_builder.py` | Миграция БД |
| MODIFY | `app/models/__init__.py` | +FoodItem |
| MODIFY | `app/models/pet.py` | удалить food_category_id |
| MODIFY | `app/models/ration.py` | daily_food_grams/food_per_meal_grams → nullable |
| MODIFY | `app/schemas/pet.py` | удалить food_category_id |
| MODIFY | `app/services/nutrition_service.py` | убрать food_category логику |
| MODIFY | `app/repositories/nutrition_repo.py` | убрать get_food_category из calculate_and_save |
| MODIFY | `app/routers/nutrition.py` | убрать /food-categories, упростить RationResponse |
| MODIFY | `app/main.py` | +router meal |
| MODIFY | `app/scheduler.py` | +кнопка «🍽 Что дать?» в пуш |
| MODIFY | `bot/states.py` | удалить waiting_food_category, +MealBuilder |
| MODIFY | `bot/keyboards.py` | удалить food_category_keyboard, +3 meal клавиатуры |
| MODIFY | `bot/handlers/pet_creation.py` | удалить шаг 9 и его обработчики |
| MODIFY | `bot/handlers/nutrition.py` | убрать граммовку, +кнопка «Подобрать порцию» |
| MODIFY | `bot/main.py` | +router meal_builder |
| MODIFY | `tests/test_meal_service.py` | тесты MealService |

---

### Task 1: DB-миграция

**Files:**
- Create: `alembic/versions/a1b2c3_meal_builder.py`
- Modify: `app/models/pet.py`
- Modify: `app/models/ration.py`
- Modify: `app/models/food_item.py`

- [ ] **Step 1: Создать `app/models/food_item.py`**

```python
from sqlalchemy import Integer, String, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    kcal_per_100g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    protein_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fat_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    carb_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    calcium_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    phosphorus_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    omega3_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    taurine_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="USDA")
```

- [ ] **Step 2: Обновить `app/models/pet.py` — удалить `food_category_id`**

Удалить строку:
```python
food_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_categories.id"), nullable=True)
```

- [ ] **Step 3: Обновить `app/models/ration.py` — сделать граммовку nullable**

```python
from datetime import datetime
from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Ration(Base):
    __tablename__ = "rations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(Integer, ForeignKey("pets.id", ondelete="CASCADE"))
    daily_calories: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    daily_food_grams: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    food_per_meal_grams: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: Добавить `FoodItem` в `app/models/__init__.py`**

```python
from app.models.user import User
from app.models.pet import Pet
from app.models.feature_flag import FeatureFlag
from app.models.ration import Ration
from app.models.nutrition_knowledge import NutritionKnowledge
from app.models.feeding_reminder import FeedingReminder
from app.models.ai_request import AiRequest
from app.models.weight_history import WeightHistory
from app.models.food_category import FoodCategory
from app.models.breed_risk import BreedRisk
from app.models.stop_food import StopFood
from app.models.breed_registry import BreedRegistry
from app.models.breed_knowledge import BreedKnowledge
from app.models.food_item import FoodItem

__all__ = ["User", "Pet", "FeatureFlag", "Ration", "NutritionKnowledge",
           "FeedingReminder", "AiRequest", "WeightHistory",
           "FoodCategory", "BreedRisk", "StopFood", "BreedRegistry",
           "BreedKnowledge", "FoodItem"]
```

- [ ] **Step 5: Создать миграцию `alembic/versions/a1b2c3_meal_builder.py`**

```python
"""meal_builder: food_items table, drop food_category_id, nullable ration grams

Revision ID: a1b2c3
Revises: (поставить id предыдущей миграции)
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3'
down_revision = None  # заменить на реальный id последней миграции
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create food_items
    op.create_table(
        'food_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('name_aliases', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('species', sa.String(50), nullable=False),
        sa.Column('kcal_per_100g', sa.Numeric(6, 2), nullable=False),
        sa.Column('protein_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('fat_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('carb_g', sa.Numeric(5, 2), nullable=False),
        sa.Column('calcium_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('phosphorus_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('omega3_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('taurine_mg', sa.Numeric(7, 2), nullable=True),
        sa.Column('source', sa.String(50), server_default='USDA'),
    )
    # 2. Drop food_category_id from pets
    op.drop_constraint('pets_food_category_id_fkey', 'pets', type_='foreignkey')
    op.drop_column('pets', 'food_category_id')
    # 3. Make ration grams nullable
    op.alter_column('rations', 'daily_food_grams', nullable=True)
    op.alter_column('rations', 'food_per_meal_grams', nullable=True)


def downgrade() -> None:
    op.add_column('pets', sa.Column('food_category_id', sa.Integer(), nullable=True))
    op.create_foreign_key('pets_food_category_id_fkey', 'pets',
                          'food_categories', ['food_category_id'], ['id'])
    op.alter_column('rations', 'daily_food_grams', nullable=False)
    op.alter_column('rations', 'food_per_meal_grams', nullable=False)
    op.drop_table('food_items')
```

- [ ] **Step 6: Найти `down_revision` и вставить реальный ID**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
alembic heads
```

Скопировать последний revision ID и вставить в `down_revision`.

- [ ] **Step 7: Применить миграцию**

```bash
alembic upgrade head
```

Ожидаем: `Running upgrade ... -> a1b2c3, meal_builder ...`

- [ ] **Step 8: Commit**

```bash
git add app/models/food_item.py app/models/pet.py app/models/ration.py \
        app/models/__init__.py alembic/versions/a1b2c3_meal_builder.py
git commit -m "feat: add food_items table, drop food_category_id, nullable ration grams"
```

---

### Task 2: Seed-данные food_items

**Files:**
- Create: `app/seeds/food_items_seed.py`

- [ ] **Step 1: Создать `app/seeds/food_items_seed.py`**

```python
"""Seed ~70 food items from USDA FoodData Central. Run once after migration."""
import asyncio
from app.database import async_session_maker
from app.models.food_item import FoodItem

ITEMS = [
    # (name, aliases_json, category, species, kcal, prot, fat, carb, ca, p, omega3, taurine)
    # ── MEAT ──
    ("курица варёная",   '["курочка","куриное","chicken"]',    "meat", "all",  165, 31.0, 3.6,  0.0, 15,  220,   50,  50),
    ("говядина варёная", '["говяжье","beef","говядина"]',       "meat", "all",  250, 26.0, 17.0, 0.0, 18,  200,   30,  35),
    ("индейка варёная",  '["индейка","turkey"]',                "meat", "all",  189, 29.0, 7.4,  0.0, 21,  218,   70,  30),
    ("кролик варёный",   '["крольчатина","rabbit"]',            "meat", "all",  197, 29.0, 8.0,  0.0, 18,  252,   20,  25),
    ("баранина варёная", '["lamb","ягнятина"]',                 "meat", "all",  258, 25.6, 16.5, 0.0, 17,  188,  100,  40),
    ("телятина варёная", '["veal","телёнок"]',                  "meat", "all",  172, 21.0, 9.4,  0.0, 14,  200,   30,  20),
    ("утка варёная",     '["duck","утятина"]',                  "meat", "all",  337, 19.0, 28.0, 0.0, 12,  185,  100,  35),
    # ── OFFAL ──
    ("говяжья печень",   '["печень","liver","liver beef"]',     "meat", "all",  135, 20.4, 3.6,  3.9,  5,  387,   20,  68),
    ("говяжье сердце",   '["сердце","heart beef"]',             "meat", "all",  112, 17.7, 3.9,  0.1,  5,  212,   20,  65),
    ("говяжьи почки",    '["почки","kidney beef"]',             "meat", "all",   99, 17.4, 3.1,  0.0, 11,  257,    0,  20),
    ("куриные желудки",  '["желудки","gizzard"]',               "meat", "all",   94, 17.7, 2.1,  0.0,  7,  180,    0,   0),
    ("рубец говяжий",    '["рубец","tripe"]',                   "meat", "all",   97, 14.5, 4.1,  0.0, 50,   80,    0,  30),
    ("куриные шейки",    '["шейки","neck chicken"]',            "meat", "all",  233, 21.0, 16.0, 0.0,100,  190,   40,  30),
    ("печень кролика",   '["rabbit liver"]',                    "meat", "all",  136, 21.0, 5.5,  0.5,  8,  349,    0,  60),
    # ── FISH ──
    ("лосось сырой",     '["salmon","сёмга","форель"]',         "fish", "all",  208, 20.4, 13.4, 0.0, 12,  240, 2600,  45),
    ("тунец сырой",      '["tuna","тунец"]',                    "fish", "all",  144, 23.3, 4.9,  0.0, 10,  278,  300,  70),
    ("треска сырая",     '["cod","треска"]',                    "fish", "all",   82, 17.8, 0.7,  0.0, 16,  203,  200,  15),
    ("сельдь сырая",     '["herring","сельдь"]',                "fish", "all",  158, 17.9, 9.0,  0.0, 57,  236, 1700,  55),
    ("скумбрия сырая",   '["mackerel","скумбрия"]',             "fish", "all",  205, 18.6, 13.9, 0.0, 12,  217, 2600,  50),
    ("сардины в воде",   '["sardine","сардина"]',               "fish", "all",  208, 24.6, 11.5, 0.0,382,  490, 1480,  40),
    # ── EGG ──
    ("куриное яйцо",     '["яйцо","egg","яйца"]',               "egg",  "all",  143, 12.6, 9.5,  0.7, 50,  172,   50,   1),
    ("перепелиное яйцо", '["перепёлка","quail egg"]',           "egg",  "all",  158, 13.0, 11.0, 0.4, 64,  226,    0,   0),
    # ── GRAIN ──
    ("гречка варёная",   '["гречневая","buckwheat","греча"]',   "grain","all",   92,  3.4, 0.6, 20.0,  7,   70,    0,   0),
    ("рис варёный",      '["рис","rice"]',                      "grain","all",  130,  2.7, 0.3, 28.0, 10,   43,    0,   0),
    ("овсянка варёная",  '["овёс","oatmeal","овсяная"]',        "grain","all",   71,  2.5, 1.4, 12.0,  9,   77,   20,   0),
    ("пшено варёное",    '["пшено","millet"]',                  "grain","all",  119,  3.5, 1.0, 23.0,  3,   74,    0,   0),
    ("перловка варёная", '["перловая","barley","ячмень"]',      "grain","all",  123,  2.3, 0.4, 28.0, 11,   54,    0,   0),
    # ── VEGETABLE ──
    ("морковь сырая",    '["морковка","carrot"]',               "vegetable","all", 41, 0.9, 0.2, 9.6, 33,   35,    0,   0),
    ("тыква варёная",    '["тыква","pumpkin"]',                 "vegetable","all", 26, 1.0, 0.1, 6.5, 21,   44,    0,   0),
    ("кабачок сырой",    '["кабачок","zucchini","цукини"]',     "vegetable","all", 17, 1.2, 0.3, 3.1, 16,   38,    0,   0),
    ("брокколи сырая",   '["брокколи","broccoli"]',             "vegetable","all", 34, 2.8, 0.4, 6.6, 47,   66,    0,   0),
    ("шпинат сырой",     '["шпинат","spinach"]',                "vegetable","all", 23, 2.9, 0.4, 3.6, 99,   49,  138,   0),
    ("огурец сырой",     '["огурец","cucumber"]',               "vegetable","all", 15, 0.7, 0.1, 3.6, 16,   24,    0,   0),
    ("зелёная фасоль",   '["стручковая","green beans"]',        "vegetable","all", 31, 1.8, 0.1, 7.0, 37,   38,    0,   0),
    ("сладкий картофель",'["батат","sweet potato"]',            "vegetable","all", 86, 1.6, 0.1,20.0, 30,   47,    0,   0),
    ("яблоко",           '["яблоко","apple"]',                  "vegetable","all", 52, 0.3, 0.2,14.0,  6,   11,    0,   0),
    ("черника",          '["черника","blueberry"]',             "vegetable","all", 57, 0.7, 0.3,14.0,  6,   12,    0,   0),
    ("горох варёный",    '["горошек","pea"]',                   "vegetable","all", 81, 5.4, 0.4,14.0, 25,  117,    0,   0),
    # ── DAIRY ──
    ("творог 5%",        '["творог","cottage cheese","curd"]',  "dairy","all",   98, 11.1, 4.3, 3.4, 83,  159,   10,   0),
    ("кефир 1%",         '["кефир","kefir"]',                   "dairy","all",   40,  3.4, 1.0, 4.7,120,   95,    0,   0),
    ("сметана 15%",      '["сметана","sour cream"]',            "dairy","all",  163,  2.4,15.0, 3.6, 85,   78,    0,   0),
    # ── OIL ──
    ("рыбий жир",        '["fish oil","омега"]',                "oil",  "all",  900,  0.0,100.0,0.0,  0,    0,30000,   0),
    ("льняное масло",    '["linseed oil","льняное"]',           "oil",  "all",  884,  0.0,100.0,0.0,  0,    0,53000,   0),
    ("оливковое масло",  '["olive oil","оливковое"]',           "oil",  "all",  884,  0.0, 99.9,0.0,  1,    0,  760,   0),
]


async def seed():
    async with async_session_maker() as session:
        for row in ITEMS:
            item = FoodItem(
                name=row[0], name_aliases=row[1], category=row[2], species=row[3],
                kcal_per_100g=row[4], protein_g=row[5], fat_g=row[6], carb_g=row[7],
                calcium_mg=row[8], phosphorus_mg=row[9], omega3_mg=row[10], taurine_mg=row[11],
                source="USDA",
            )
            session.add(item)
        await session.commit()
    print(f"Seeded {len(ITEMS)} food items.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Запустить seed**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
python -m app.seeds.food_items_seed
```

Ожидаем: `Seeded 44 food items.`

- [ ] **Step 3: Commit**

```bash
git add app/seeds/food_items_seed.py
git commit -m "feat: seed food_items from USDA data"
```

---

### Task 3: Упрощение NutritionService и схем

**Files:**
- Modify: `app/schemas/pet.py`
- Modify: `app/services/nutrition_service.py`
- Modify: `app/repositories/nutrition_repo.py`
- Modify: `app/routers/nutrition.py`

- [ ] **Step 1: Обновить `app/schemas/pet.py` — удалить `food_category_id`**

```python
from datetime import datetime
from pydantic import BaseModel, field_validator

ALLOWED_SPECIES = ["cat", "dog", "rodent", "bird", "reptile"]
ALLOWED_GOALS = ["maintain", "lose", "gain", "growth"]
ALLOWED_ACTIVITY = ["low", "moderate", "high", "working"]
ALLOWED_PHYSIO = ["normal", "pregnant", "lactating", "recovery"]


class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None = None
    age_months: int
    weight_kg: float
    goal: str = "maintain"
    is_neutered: bool = False
    activity_level: str = "moderate"
    physio_status: str = "normal"

    @field_validator("species")
    @classmethod
    def validate_species(cls, v):
        if v not in ALLOWED_SPECIES:
            raise ValueError(f"invalid_species. Allowed: {ALLOWED_SPECIES}")
        return v

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, v):
        if v <= 0:
            raise ValueError("weight_kg must be > 0")
        return v

    @field_validator("activity_level")
    @classmethod
    def validate_activity(cls, v):
        if v not in ALLOWED_ACTIVITY:
            raise ValueError(f"invalid_activity. Allowed: {ALLOWED_ACTIVITY}")
        return v

    @field_validator("physio_status")
    @classmethod
    def validate_physio(cls, v):
        if v not in ALLOWED_PHYSIO:
            raise ValueError(f"invalid_physio. Allowed: {ALLOWED_PHYSIO}")
        return v


class PetUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    age_months: int | None = None
    weight_kg: float | None = None
    goal: str | None = None
    is_neutered: bool | None = None
    activity_level: str | None = None
    physio_status: str | None = None


class PetResponse(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None
    age_months: int
    weight_kg: float
    goal: str
    is_neutered: bool
    activity_level: str
    physio_status: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Обновить `app/services/nutrition_service.py` — убрать food_category**

```python
from dataclasses import dataclass
from app.models.pet import Pet
from app.models.ration import Ration
from app.repositories.nutrition_repo import NutritionRepository

ACTIVITY_MULTIPLIER = {
    "low": 0.8,
    "moderate": 1.0,
    "high": 1.2,
    "working": 1.6,
}
_DEFAULT_KCAL = 350.0  # used only for protein/fat minimum estimation


class MERCalculator:
    def __init__(self, weight_kg: float, age_months: int, is_neutered: bool,
                 activity_level: str, physio_status: str, goal: str,
                 breed_risks: list[str]):
        self.weight_kg = weight_kg
        self.age_months = age_months
        self.is_neutered = is_neutered
        self.activity_level = activity_level
        self.physio_status = physio_status
        self.goal = goal
        self.breed_risks = breed_risks

    def rer(self) -> float:
        return 70 * (self.weight_kg ** 0.75)

    def _base_coefficient(self) -> float:
        if self.age_months < 4:
            return 3.0
        if self.age_months < 12:
            return 2.0
        if self.physio_status in ("pregnant", "lactating"):
            return 2.5
        if self.physio_status == "recovery":
            return 1.3
        if self.goal == "lose" or "obesity" in self.breed_risks:
            return 1.4
        if self.is_neutered:
            return 1.6
        return 1.8

    def mer(self) -> float:
        multiplier = ACTIVITY_MULTIPLIER.get(self.activity_level, 1.0)
        return self.rer() * self._base_coefficient() * multiplier

    def meals_per_day(self) -> int:
        if self.age_months < 4:
            return 5
        if self.age_months < 6:
            return 4
        if self.age_months < 12:
            return 3
        return 2

    def daily_food_grams(self, kcal_per_100g: float) -> float:
        return (self.mer() / kcal_per_100g) * 100

    def _is_puppy(self) -> bool:
        return self.age_months < 12 or self.physio_status in ("pregnant", "lactating")

    def protein_min_g(self, daily_food_grams: float) -> float:
        pct = 0.225 if self._is_puppy() else 0.18
        return daily_food_grams * pct

    def fat_min_g(self, daily_food_grams: float) -> float:
        pct = 0.085 if self._is_puppy() else 0.055
        return daily_food_grams * pct

    def has_hypoglycemia_risk(self) -> bool:
        return self.age_months < 4 and "hypoglycemia_puppies" in self.breed_risks

    def recommendations(self) -> list[str]:
        notes = []
        notes.append("При смене корма — переход 7–10 дней")
        notes.append("Рекомендуется миска-лабиринт")
        if "atopy" in self.breed_risks:
            notes.append("Омега-3 добавки полезны для кожи и шерсти (предрасположенность к атопии)")
        if "patellar_luxation" in self.breed_risks:
            notes.append("Глюкозамин + хондроитин + Омега-3 для суставов (пателлярная люксация)")
        if self.activity_level == "working":
            notes.append("Рабочая собака: потребность в калориях существенно выше стандарта")
        return notes


@dataclass
class RationResult:
    daily_calories: float
    meals_per_day: int
    protein_min_g: float
    fat_min_g: float
    stop_foods_level1: list[dict]
    stop_foods_level2: list[dict]
    stop_foods_level3: list[dict]
    recommendations: list[str]
    hypoglycemia_warning: bool
    notes: str
    ration: Ration


class NutritionService:
    def __init__(self, repo: NutritionRepository):
        self.repo = repo

    async def calculate_and_save(self, pet: Pet) -> RationResult:
        weight = float(pet.weight_kg)
        breed_risks = await self.repo.get_breed_risks(pet.breed or "")

        calc = MERCalculator(
            weight_kg=weight,
            age_months=pet.age_months,
            is_neutered=pet.is_neutered,
            activity_level=pet.activity_level,
            physio_status=pet.physio_status,
            goal=pet.goal,
            breed_risks=breed_risks,
        )

        mer = round(calc.mer(), 1)
        meals = calc.meals_per_day()
        daily_grams_est = round(calc.daily_food_grams(_DEFAULT_KCAL), 1)
        protein_g = round(calc.protein_min_g(daily_grams_est), 1)
        fat_g = round(calc.fat_min_g(daily_grams_est), 1)

        stop1 = await self.repo.get_stop_foods(pet.species, level=1)
        stop2 = await self.repo.get_stop_foods(pet.species, level=2)
        stop3 = await self.repo.get_stop_foods(pet.species, level=3)

        ration = await self.repo.upsert_ration(
            pet_id=pet.id,
            daily_calories=mer,
            meals_per_day=meals,
            notes="; ".join(calc.recommendations()),
        )

        return RationResult(
            daily_calories=mer,
            meals_per_day=meals,
            protein_min_g=protein_g,
            fat_min_g=fat_g,
            stop_foods_level1=stop1,
            stop_foods_level2=stop2,
            stop_foods_level3=stop3,
            recommendations=calc.recommendations(),
            hypoglycemia_warning=calc.has_hypoglycemia_risk(),
            notes="; ".join(calc.recommendations()),
            ration=ration,
        )

    async def get_ration(self, pet_id: int) -> Ration | None:
        return await self.repo.get_ration_by_pet(pet_id)
```

- [ ] **Step 3: Обновить `app/repositories/nutrition_repo.py` — убрать food_category из upsert_ration**

Изменить сигнатуру `upsert_ration`:

```python
async def upsert_ration(self, pet_id: int, daily_calories: float,
                        meals_per_day: int, notes: str | None) -> Ration:
    existing = await self.get_ration_by_pet(pet_id)
    if existing:
        existing.daily_calories = daily_calories
        existing.meals_per_day = meals_per_day
        existing.notes = notes
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
    ration = Ration(
        pet_id=pet_id,
        daily_calories=daily_calories,
        meals_per_day=meals_per_day,
        notes=notes,
    )
    self.session.add(ration)
    await self.session.commit()
    await self.session.refresh(ration)
    return ration
```

- [ ] **Step 4: Обновить `app/routers/nutrition.py` — убрать /food-categories и упростить RationResponse**

```python
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.nutrition_repo import NutritionRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


class StopFoodItem(BaseModel):
    product_name: str
    toxic_component: str | None
    clinical_effect: str | None


class RationResponse(BaseModel):
    pet_id: int
    daily_calories: float
    meals_per_day: int
    protein_min_g: float
    fat_min_g: float
    stop_foods_level1: list[StopFoodItem]
    stop_foods_level2: list[StopFoodItem]
    stop_foods_level3: list[StopFoodItem]
    recommendations: list[str]
    hypoglycemia_warning: bool
    notes: str


@router.get("/{pet_id}", response_model=RationResponse)
async def get_ration(pet_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(
        telegram_id=request.state.telegram_id
    )
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    service = NutritionService(NutritionRepository(db))
    result = await service.calculate_and_save(pet)

    return RationResponse(
        pet_id=pet.id,
        daily_calories=result.daily_calories,
        meals_per_day=result.meals_per_day,
        protein_min_g=result.protein_min_g,
        fat_min_g=result.fat_min_g,
        stop_foods_level1=[StopFoodItem(**s) for s in result.stop_foods_level1],
        stop_foods_level2=[StopFoodItem(**s) for s in result.stop_foods_level2],
        stop_foods_level3=[StopFoodItem(**s) for s in result.stop_foods_level3],
        recommendations=result.recommendations,
        hypoglycemia_warning=result.hypoglycemia_warning,
        notes=result.notes,
    )
```

- [ ] **Step 5: Запустить тесты**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
pytest tests/test_nutrition_service.py -v
```

Ожидаем: все тесты PASS (тесты MERCalculator не зависят от food_category).

- [ ] **Step 6: Commit**

```bash
git add app/schemas/pet.py app/services/nutrition_service.py \
        app/repositories/nutrition_repo.py app/routers/nutrition.py
git commit -m "refactor: remove food_category from Pet and NutritionService"
```

---

### Task 4: Упрощение бота — удаление шага 9 и обновление отображения рациона

**Files:**
- Modify: `bot/states.py`
- Modify: `bot/keyboards.py`
- Modify: `bot/handlers/pet_creation.py`
- Modify: `bot/handlers/nutrition.py`

- [ ] **Step 1: Обновить `bot/states.py` — удалить `waiting_food_category`**

```python
from aiogram.fsm.state import State, StatesGroup


class PetCreation(StatesGroup):
    waiting_species        = State()
    waiting_breed          = State()
    waiting_breed_text     = State()
    waiting_breed_photo    = State()
    waiting_breed_suggest  = State()
    waiting_name           = State()
    waiting_age_unit       = State()
    waiting_age            = State()
    waiting_weight         = State()
    waiting_neutered       = State()
    waiting_activity       = State()
    waiting_confirm        = State()
```

- [ ] **Step 2: Обновить `bot/keyboards.py` — удалить `food_category_keyboard`**

Удалить функцию `food_category_keyboard` целиком. Остальные функции не трогать.

- [ ] **Step 3: Обновить `bot/handlers/pet_creation.py` — убрать шаг 9**

Изменить `process_activity` — теперь сразу переходит к подтверждению:

```python
@router.callback_query(PetCreation.waiting_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split(":")[1]
    await state.update_data(activity_level=activity)
    data = await state.get_data()

    breed_label = data.get("breed") or "Метис"
    neutered_label = "Да" if data.get("is_neutered") else "Нет"
    activity_label = ACTIVITY_LABELS.get(activity, activity)

    summary = (
        f"Проверь данные питомца\n\n"
        f"<b>{data['name']}</b>\n"
        f"Вид:          {SPECIES_LABELS.get(data['species'], data['species'])}\n"
        f"Порода:       {breed_label}\n"
        f"Возраст:      {data.get('age_display', str(data['age_months']) + ' мес')}\n"
        f"Вес:          {data['weight_kg']} кг\n"
        f"Кастрирован:  {neutered_label}\n"
        f"Активность:   {activity_label}"
    )
    await state.set_state(PetCreation.waiting_confirm)
    await callback.message.edit_text(summary, parse_mode="HTML", reply_markup=confirm_keyboard())
```

Удалить:
- Импорт `food_category_keyboard` из keyboards
- Хендлеры `process_food_category` и `back_from_food_category`
- Хендлер `back_from_confirm` (убрать вызов `/food-categories`)
- В `confirm_save` убрать `food_category_id` из JSON тела запроса

Обновить `confirm_save`:

```python
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:save")
async def confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/pets",
            json={
                "name": data["name"],
                "species": data["species"],
                "breed": data.get("breed"),
                "age_months": data["age_months"],
                "weight_kg": data["weight_kg"],
                "goal": "maintain",
                "is_neutered": data.get("is_neutered", False),
                "activity_level": data.get("activity_level", "moderate"),
                "physio_status": data.get("physio_status", "normal"),
            },
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code == 201:
        pet = resp.json()
        await state.set_state(None)
        await state.update_data(active_pet_id=pet["id"], active_pet_name=pet["name"])
        await callback.message.edit_text(
            f"Профиль создан! Теперь я знаю как кормить <b>{data['name']}</b>.\n\n"
            "Выбери что хочешь сделать:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(data["name"])
        )
    else:
        await state.clear()
        await callback.message.edit_text("Что-то пошло не так. Попробуй ещё раз /start")
```

Обновить `back_from_confirm`:

```python
@router.callback_query(PetCreation.waiting_confirm, F.data == "back")
async def back_from_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_activity)
    await callback.message.edit_text(
        "Шаг 8 из 8\nУровень активности питомца?",
        reply_markup=activity_keyboard()
    )
```

- [ ] **Step 4: Обновить `bot/handlers/nutrition.py` — убрать граммовку, добавить кнопку**

Изменить `_show_ration`:

```python
async def _show_ration(callback: CallbackQuery, pet: dict, telegram_id: int, pet_name: str = ""):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/nutrition/{pet['id']}",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    if resp.status_code != 200:
        await callback.message.edit_text("Не удалось рассчитать рацион. Попробуй позже.")
        return
    r = resp.json()

    text = (
        f"Рацион для <b>{pet['name']}</b>\n"
        f"Вес: {pet['weight_kg']} кг\n\n"
        f"<b>Энергия</b>\n"
        f"Калорий в день:  <b>{r['daily_calories']} ккал</b>\n"
        f"Кормлений:       <b>{r['meals_per_day']} раза в день</b>\n\n"
        f"<b>Нутриенты (минимум)</b>\n"
        f"Белок:  {r['protein_min_g']} г/день\n"
        f"Жир:    {r['fat_min_g']} г/день\n"
        f"Ca:P    оптимум 1.2–1.4:1\n"
    )

    if r.get("hypoglycemia_warning"):
        text += "\n⚠️ Щенок до 4 мес — не пропускай кормления! Риск гипогликемии.\n"

    if r.get("recommendations"):
        text += "\n<b>Рекомендации</b>\n"
        for rec in r["recommendations"]:
            text += f"• {rec}\n"

    text += "\n<i>⚠️ Расчёт — отправная точка. Индивидуальная потребность может отличаться на ±30%.</i>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Подобрать порцию",
                              callback_data=f"meal_start:{pet['id']}")],
        [InlineKeyboardButton(text="← Главное меню", callback_data="menu:back")],
    ])

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest:
        pass
```

- [ ] **Step 5: Commit**

```bash
git add bot/states.py bot/keyboards.py bot/handlers/pet_creation.py \
        bot/handlers/nutrition.py
git commit -m "refactor: remove pet creation step 9, simplify ration display"
```

---

### Task 5: MealRepository

**Files:**
- Create: `app/repositories/meal_repo.py`

- [ ] **Step 1: Создать `app/repositories/meal_repo.py`**

```python
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.food_item import FoodItem
from app.models.stop_food import StopFood
from app.redis_client import get_redis

MEAL_SESSION_TTL = 1800   # 30 min
DEEPSEEK_CACHE_TTL = 86400  # 24h


class MealRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── food_items ──────────────────────────────────────────────────

    async def get_all_food_items(self) -> list[FoodItem]:
        result = await self.session.execute(select(FoodItem))
        return list(result.scalars().all())

    async def get_stop_foods_for_species(self, species: str) -> list[StopFood]:
        result = await self.session.execute(
            select(StopFood).where(StopFood.species.in_([species, "all"]))
        )
        return list(result.scalars().all())

    # ── Redis meal session ──────────────────────────────────────────

    def _session_key(self, telegram_id: int, pet_id: int) -> str:
        return f"meal:{telegram_id}:{pet_id}"

    async def get_session(self, telegram_id: int, pet_id: int) -> dict | None:
        redis = get_redis()
        raw = await redis.get(self._session_key(telegram_id, pet_id))
        return json.loads(raw) if raw else None

    async def save_session(self, telegram_id: int, pet_id: int, data: dict) -> None:
        redis = get_redis()
        await redis.set(
            self._session_key(telegram_id, pet_id),
            json.dumps(data, ensure_ascii=False),
            ex=MEAL_SESSION_TTL,
        )

    async def delete_session(self, telegram_id: int, pet_id: int) -> None:
        redis = get_redis()
        await redis.delete(self._session_key(telegram_id, pet_id))

    async def undo_last_item(self, telegram_id: int, pet_id: int) -> dict | None:
        """Remove last item from session. Returns updated session or None."""
        session = await self.get_session(telegram_id, pet_id)
        if not session or not session.get("items"):
            return None
        session["items"].pop()
        await self.save_session(telegram_id, pet_id, session)
        return session

    # ── DeepSeek cache ──────────────────────────────────────────────

    def _deepseek_key(self, product_name: str) -> str:
        return f"meal_ds:{product_name.lower().strip()}"

    async def get_cached_lookup(self, product_name: str) -> dict | None:
        redis = get_redis()
        raw = await redis.get(self._deepseek_key(product_name))
        return json.loads(raw) if raw else None

    async def cache_lookup(self, product_name: str, result: dict) -> None:
        redis = get_redis()
        await redis.set(
            self._deepseek_key(product_name),
            json.dumps(result, ensure_ascii=False),
            ex=DEEPSEEK_CACHE_TTL,
        )
```

- [ ] **Step 2: Commit**

```bash
git add app/repositories/meal_repo.py
git commit -m "feat: add MealRepository with Redis session and food_items queries"
```

---

### Task 6: MealService

**Files:**
- Create: `app/services/meal_service.py`

- [ ] **Step 1: Создать `app/services/meal_service.py`**

```python
import json
import logging
from dataclasses import dataclass
from rapidfuzz import process as fuzz_process, fuzz
from openai import AsyncOpenAI
from app.config import settings
from app.models.food_item import FoodItem
from app.models.stop_food import StopFood
from app.repositories.meal_repo import MealRepository

logger = logging.getLogger(__name__)

SPECIES_MICROS: dict[str, list[str]] = {
    "cat":     ["taurine_mg", "omega3_mg", "calcium_mg", "phosphorus_mg"],
    "dog":     ["omega3_mg", "calcium_mg", "phosphorus_mg"],
    "rodent":  ["calcium_mg", "phosphorus_mg"],
    "bird":    ["calcium_mg"],
    "reptile": ["calcium_mg", "phosphorus_mg"],
}
RISK_BOOST: dict[str, list[str]] = {
    "atopy":             ["omega3_mg"],
    "patellar_luxation": ["omega3_mg"],
}
RANGE_GUARD: dict[str, tuple[float, float]] = {
    "meat":      (80, 400),
    "fish":      (80, 300),
    "egg":       (130, 160),
    "grain":     (60, 380),
    "vegetable": (15, 100),
    "dairy":     (30, 400),
    "oil":       (700, 900),
}
# Minimum nutrients per 1000 kcal (NRC 2006)
MICRO_PER_1000KCAL: dict[str, dict[str, float]] = {
    "dog":  {"calcium_mg": 1250, "phosphorus_mg": 1000, "omega3_mg": 110},
    "cat":  {"taurine_mg": 500,  "omega3_mg": 110, "calcium_mg": 720, "phosphorus_mg": 640},
}
EXAMPLES_BY_TYPE: dict[str, str] = {
    "natural":  "курица, говядина, гречка, морковь, яйцо",
    "prepared": "Royal Canin, Purina Pro Plan, Hills",
    "mixed":    "курица + гречка + сухой корм",
}


@dataclass
class StopCheckResult:
    level: int | None       # 1, 2, 3, or None
    product_name: str | None
    toxic_component: str | None
    clinical_effect: str | None


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


class MealService:
    def __init__(self, repo: MealRepository):
        self.repo = repo
        self._deepseek = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )

    # ── Public API ──────────────────────────────────────────────────

    def get_required_micros(self, species: str, breed_risks: list[str]) -> list[str]:
        micros = list(SPECIES_MICROS.get(species, ["calcium_mg", "phosphorus_mg"]))
        for risk in breed_risks:
            for extra in RISK_BOOST.get(risk, []):
                if extra not in micros:
                    micros.append(extra)
        return micros

    def compute_micro_targets(self, mer: float, meals_per_day: int,
                               species: str, required_micros: list[str]) -> dict:
        per_1000 = MICRO_PER_1000KCAL.get(species, {})
        targets = {}
        for micro in required_micros:
            if micro in per_1000:
                targets[micro] = round(per_1000[micro] * mer / 1000 / meals_per_day, 1)
        return targets

    def check_stop_list(self, product_name: str,
                        stop_foods: list[StopFood]) -> StopCheckResult:
        names = [sf.product_name for sf in stop_foods]
        match = fuzz_process.extractOne(
            product_name, names,
            scorer=fuzz.WRatio,
            score_cutoff=75,
        )
        if match is None:
            return StopCheckResult(None, None, None, None)
        idx = names.index(match[0])
        sf = stop_foods[idx]
        return StopCheckResult(
            level=sf.level,
            product_name=sf.product_name,
            toxic_component=sf.toxic_component,
            clinical_effect=sf.clinical_effect,
        )

    def search_food_item(self, product_name: str,
                         food_items: list[FoodItem]) -> FoodItem | None:
        # Build search corpus: name + aliases
        corpus: list[tuple[str, FoodItem]] = []
        for fi in food_items:
            corpus.append((fi.name, fi))
            if fi.name_aliases:
                try:
                    aliases = json.loads(fi.name_aliases)
                    for alias in aliases:
                        corpus.append((alias, fi))
                except (json.JSONDecodeError, TypeError):
                    pass

        texts = [c[0] for c in corpus]
        match = fuzz_process.extractOne(
            product_name, texts,
            scorer=fuzz.WRatio,
            score_cutoff=80,
        )
        if match is None:
            return None
        idx = texts.index(match[0])
        return corpus[idx][1]

    async def lookup_product(self, product_name: str) -> FoodLookupResult | None:
        """Search DB first, fallback to DeepSeek."""
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
            )
        return await self._deepseek_lookup(product_name)

    def calculate_grams(self, gap_kcal: float, kcal_per_100g: float) -> float:
        raw = gap_kcal * 0.5 / (kcal_per_100g / 100)
        return round(max(20.0, min(200.0, raw)), 0)

    def calculate_progress(self, items: list[dict], target: dict) -> dict:
        totals = self._sum_items(items)
        progress = {}
        for key, tval in target.items():
            if tval and tval > 0:
                progress[f"{key}_pct"] = round(totals.get(key, 0) / tval * 100, 0)
        return progress

    def is_done(self, items: list[dict], target: dict) -> bool:
        totals = self._sum_items(items)
        kcal_pct = totals.get("kcal", 0) / target.get("kcal", 1) * 100
        prot_pct = totals.get("protein_g", 0) / target.get("protein_g", 1) * 100
        return kcal_pct >= 90 and prot_pct >= 90

    def get_recommendation(self, items: list[dict], target: dict,
                           food_items: list[FoodItem], species: str) -> str:
        totals = self._sum_items(items)
        gap_kcal = target.get("kcal", 0) - totals.get("kcal", 0)
        gap_prot = target.get("protein_g", 0) - totals.get("protein_g", 0)
        gap_fat  = target.get("fat_g", 0) - totals.get("fat_g", 0)

        # Find candidate from food_items that covers largest gap
        candidates = [f for f in food_items if f.species in (species, "all")]
        if not candidates:
            return ""

        # Score by biggest kcal gap coverage first
        def score(fi: FoodItem) -> float:
            return (
                float(fi.kcal_per_100g) * 0.5
                + float(fi.protein_g) * 2.0 * (1 if gap_prot > 0 else 0)
                + float(fi.fat_g) * 1.0 * (1 if gap_fat > 0 else 0)
            )

        best = max(candidates, key=score)
        parts = []
        if gap_kcal > target.get("kcal", 1) * 0.15:
            parts.append("калорий")
        if gap_prot > target.get("protein_g", 1) * 0.15:
            parts.append("белка")
        if gap_fat > target.get("fat_g", 1) * 0.15:
            parts.append("жиров")

        if parts:
            return f"Не хватает {', '.join(parts)}. Попробуй добавить {best.name}."
        return f"Осталось совсем немного. Можно добавить {best.name}."

    def get_summary_tip(self, totals: dict, target: dict,
                        required_micros: list[str]) -> str:
        tips = []
        ca = totals.get("calcium_mg", 0)
        p  = totals.get("phosphorus_mg", 0)
        if p > 0 and (ca / p) < 1.2:
            tips.append("Ca:P ниже нормы — добавь яичную скорлупу или кунжут")
        for micro in required_micros:
            if micro in ("calcium_mg", "phosphorus_mg"):
                continue
            tval = target.get(micro, 0)
            got  = totals.get(micro, 0)
            if tval > 0 and got < tval * 0.9:
                if micro == "omega3_mg":
                    tips.append("Не хватает Омега-3 — добавь ½ ч.л. льняного или рыбьего масла")
                elif micro == "taurine_mg":
                    tips.append("Не хватает таурина — обязателен для кошек в натуральном рационе")
        return ". ".join(tips) if tips else ""

    # ── Private helpers ─────────────────────────────────────────────

    def _sum_items(self, items: list[dict]) -> dict:
        keys = ["kcal", "protein_g", "fat_g", "carb_g",
                "calcium_mg", "phosphorus_mg", "omega3_mg", "taurine_mg"]
        return {k: round(sum(i.get(k, 0) for i in items), 2) for k in keys}

    async def _deepseek_lookup(self, product_name: str) -> FoodLookupResult | None:
        cached = await self.repo.get_cached_lookup(product_name)
        if cached:
            return self._dict_to_lookup(product_name, cached)

        prompt = (
            f"Дай точные данные КБЖУ и микронутриентов на 100г для продукта: «{product_name}».\n"
            "Ответь ТОЛЬКО в JSON без пояснений:\n"
            '{"kcal":0,"protein_g":0,"fat_g":0,"carb_g":0,'
            '"calcium_mg":0,"phosphorus_mg":0,"omega3_mg":0,"taurine_mg":0,'
            '"category":"meat","confidence":0.9}'
        )
        try:
            response = await self._deepseek.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            # strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
        except Exception as e:
            logger.error(f"DeepSeek lookup failed for '{product_name}': {e}")
            return None

        if not self._validate_range(data.get("category", ""), data.get("kcal", 0)):
            logger.warning(f"Range guard failed for '{product_name}': {data}")
            return None
        if not self._validate_math(data):
            logger.warning(f"Math guard failed for '{product_name}': {data}")
            return None

        await self.repo.cache_lookup(product_name, data)
        return self._dict_to_lookup(product_name, data)

    def _validate_range(self, category: str, kcal: float) -> bool:
        if category not in RANGE_GUARD:
            return True
        lo, hi = RANGE_GUARD[category]
        return lo <= kcal <= hi

    def _validate_math(self, data: dict) -> bool:
        kcal = data.get("kcal", 0)
        if kcal <= 0:
            return False
        calc = (data.get("protein_g", 0) * 4
                + data.get("fat_g", 0) * 9
                + data.get("carb_g", 0) * 4)
        if kcal == 0:
            return False
        return abs(calc - kcal) / kcal <= 0.15

    def _dict_to_lookup(self, name: str, d: dict) -> FoodLookupResult:
        conf = d.get("confidence", 1.0)
        return FoodLookupResult(
            name=name, grams=0,
            kcal=float(d.get("kcal", 0)),
            protein_g=float(d.get("protein_g", 0)),
            fat_g=float(d.get("fat_g", 0)),
            carb_g=float(d.get("carb_g", 0)),
            calcium_mg=float(d.get("calcium_mg", 0)),
            phosphorus_mg=float(d.get("phosphorus_mg", 0)),
            omega3_mg=float(d.get("omega3_mg", 0)),
            taurine_mg=float(d.get("taurine_mg", 0)),
            source="deepseek_cache",
            confidence=conf,
            low_confidence=conf < 0.7,
        )
```

- [ ] **Step 2: Commit**

```bash
git add app/services/meal_service.py
git commit -m "feat: add MealService with fuzzy search, stop-list, DeepSeek fallback"
```

---

### Task 7: Тесты MealService

**Files:**
- Modify: `tests/test_meal_service.py`

- [ ] **Step 1: Написать тесты**

```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.meal_service import MealService, RANGE_GUARD
from app.models.food_item import FoodItem
from app.models.stop_food import StopFood


def make_service() -> MealService:
    repo = AsyncMock()
    svc = MealService(repo)
    return svc


def make_food_item(name: str, aliases: list[str], category: str,
                   kcal: float, prot: float, fat: float, carb: float,
                   ca: float = 0, p: float = 0, omega: float = 0, tau: float = 0) -> FoodItem:
    fi = FoodItem()
    fi.name = name
    fi.name_aliases = json.dumps(aliases)
    fi.category = category
    fi.species = "all"
    fi.kcal_per_100g = kcal
    fi.protein_g = prot
    fi.fat_g = fat
    fi.carb_g = carb
    fi.calcium_mg = ca
    fi.phosphorus_mg = p
    fi.omega3_mg = omega
    fi.taurine_mg = tau
    return fi


def make_stop_food(name: str, level: int, species: str = "all",
                   toxic: str = "", effect: str = "") -> StopFood:
    sf = StopFood()
    sf.product_name = name
    sf.level = level
    sf.species = species
    sf.toxic_component = toxic
    sf.clinical_effect = effect
    return sf


class TestGetRequiredMicros:
    def test_dog_base(self):
        svc = make_service()
        micros = svc.get_required_micros("dog", [])
        assert "omega3_mg" in micros
        assert "calcium_mg" in micros
        assert "taurine_mg" not in micros

    def test_cat_has_taurine(self):
        svc = make_service()
        micros = svc.get_required_micros("cat", [])
        assert "taurine_mg" in micros

    def test_risk_boost_atopy(self):
        svc = make_service()
        micros = svc.get_required_micros("dog", ["atopy"])
        assert micros.count("omega3_mg") == 1


class TestCheckStopList:
    def test_level1_exact(self):
        svc = make_service()
        stops = [make_stop_food("виноград", 1, toxic="танины", effect="почечная недостаточность")]
        result = svc.check_stop_list("виноград", stops)
        assert result.level == 1
        assert result.toxic_component == "танины"

    def test_level1_fuzzy(self):
        svc = make_service()
        stops = [make_stop_food("виноград", 1)]
        result = svc.check_stop_list("виноградик", stops)
        assert result.level == 1

    def test_not_in_stoplist(self):
        svc = make_service()
        stops = [make_stop_food("виноград", 1)]
        result = svc.check_stop_list("курица", stops)
        assert result.level is None

    def test_level2(self):
        svc = make_service()
        stops = [make_stop_food("молоко", 2)]
        result = svc.check_stop_list("молоко", stops)
        assert result.level == 2


class TestSearchFoodItem:
    def test_exact_match(self):
        svc = make_service()
        chicken = make_food_item("курица варёная", ["курочка", "chicken"], "meat",
                                  165, 31, 3.6, 0)
        result = svc.search_food_item("курица", [chicken])
        assert result is not None
        assert result.name == "курица варёная"

    def test_alias_match(self):
        svc = make_service()
        chicken = make_food_item("курица варёная", ["курочка", "chicken"], "meat",
                                  165, 31, 3.6, 0)
        result = svc.search_food_item("курочка", [chicken])
        assert result is not None

    def test_no_match_below_threshold(self):
        svc = make_service()
        chicken = make_food_item("курица варёная", ["курочка"], "meat", 165, 31, 3.6, 0)
        result = svc.search_food_item("говядина", [chicken])
        assert result is None


class TestCalculateGrams:
    def test_clamp_min(self):
        svc = make_service()
        grams = svc.calculate_grams(gap_kcal=5, kcal_per_100g=165)
        assert grams == 20

    def test_clamp_max(self):
        svc = make_service()
        grams = svc.calculate_grams(gap_kcal=5000, kcal_per_100g=165)
        assert grams == 200

    def test_normal_case(self):
        svc = make_service()
        # gap=250, kcal=165 → 250*0.5/(1.65) ≈ 75.8 → 76
        grams = svc.calculate_grams(gap_kcal=250, kcal_per_100g=165)
        assert 70 <= grams <= 80


class TestValidation:
    def test_range_guard_pass(self):
        svc = make_service()
        assert svc._validate_range("meat", 200) is True

    def test_range_guard_fail_high(self):
        svc = make_service()
        assert svc._validate_range("meat", 500) is False

    def test_range_guard_fail_low(self):
        svc = make_service()
        assert svc._validate_range("vegetable", 200) is False

    def test_math_guard_pass(self):
        svc = make_service()
        data = {"kcal": 165, "protein_g": 31, "fat_g": 3.6, "carb_g": 0}
        # 31*4 + 3.6*9 + 0 = 124+32.4 = 156.4  delta=8.6/165=5% ✓
        assert svc._validate_math(data) is True

    def test_math_guard_fail(self):
        svc = make_service()
        data = {"kcal": 500, "protein_g": 5, "fat_g": 1, "carb_g": 0}
        # 5*4+1*9=29, delta=471/500=94% ✗
        assert svc._validate_math(data) is False

    def test_math_guard_zero_kcal(self):
        svc = make_service()
        data = {"kcal": 0, "protein_g": 10, "fat_g": 1, "carb_g": 0}
        assert svc._validate_math(data) is False


class TestIsDone:
    def test_done_when_90pct(self):
        svc = make_service()
        items = [{"kcal": 230, "protein_g": 28, "fat_g": 8, "carb_g": 10,
                  "calcium_mg": 0, "phosphorus_mg": 0, "omega3_mg": 0, "taurine_mg": 0}]
        target = {"kcal": 250, "protein_g": 30, "fat_g": 8}
        assert svc.is_done(items, target) is True

    def test_not_done_when_60pct(self):
        svc = make_service()
        items = [{"kcal": 150, "protein_g": 15, "fat_g": 4, "carb_g": 0,
                  "calcium_mg": 0, "phosphorus_mg": 0, "omega3_mg": 0, "taurine_mg": 0}]
        target = {"kcal": 250, "protein_g": 30, "fat_g": 8}
        assert svc.is_done(items, target) is False
```

- [ ] **Step 2: Запустить тесты**

```bash
pytest tests/test_meal_service.py -v
```

Ожидаем: все тесты PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_meal_service.py
git commit -m "test: add MealService unit tests"
```

---

### Task 8: MealRouter API

**Files:**
- Create: `app/routers/meal.py`
- Modify: `app/main.py`

- [ ] **Step 1: Создать `app/routers/meal.py`**

```python
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.nutrition_repo import NutritionRepository
from app.repositories.meal_repo import MealRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.meal_service import MealService

router = APIRouter(prefix="/meal", tags=["meal"])


class AddProductRequest(BaseModel):
    pet_id: int
    product_name: str
    food_type: str  # natural | prepared | mixed
    force_add: bool = False  # bypass Level 2 stop-list warning


@router.post("/add-product")
async def add_product(body: AddProductRequest, request: Request,
                      db: AsyncSession = Depends(get_db)):
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

    svc = MealService(MealRepository(db))
    breed_risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")
    required_micros = svc.get_required_micros(pet.species, breed_risks)

    # Get or create session
    session = await MealRepository(db).get_session(telegram_id, body.pet_id)
    if session is None:
        micro_targets = svc.compute_micro_targets(
            mer=float(ration.daily_calories),
            meals_per_day=ration.meals_per_day,
            species=pet.species,
            required_micros=required_micros,
        )
        target_kcal = round(float(ration.daily_calories) / ration.meals_per_day, 1)
        # Estimate protein/fat targets per meal using same _DEFAULT_KCAL logic
        daily_grams_est = float(ration.daily_calories) / 350 * 100
        pct_prot = 0.225 if pet.age_months < 12 else 0.18
        pct_fat  = 0.085 if pet.age_months < 12 else 0.055
        session = {
            "food_type": body.food_type,
            "items": [],
            "target": {
                "kcal": target_kcal,
                "protein_g": round(daily_grams_est * pct_prot / ration.meals_per_day, 1),
                "fat_g": round(daily_grams_est * pct_fat / ration.meals_per_day, 1),
                **micro_targets,
            },
        }

    repo = MealRepository(db)

    # 1. Check stop-list (unless force_add for Level 2)
    if not body.force_add:
        stop_foods = await repo.get_stop_foods_for_species(pet.species)
        stop_result = svc.check_stop_list(body.product_name, stop_foods)
        if stop_result.level == 1:
            return {
                "status": "blocked",
                "message": (
                    f"⛔ {stop_result.product_name} нельзя давать этому виду животных! "
                    f"Токсичный компонент: {stop_result.toxic_component}. "
                    f"Эффект: {stop_result.clinical_effect}."
                ),
            }
        if stop_result.level == 2:
            return {
                "status": "warning",
                "message": (
                    f"⚠️ {stop_result.product_name} нежелательно давать регулярно. "
                    f"{stop_result.clinical_effect or ''}. Добавить всё равно?"
                ),
                "product_name": body.product_name,
            }

    # 2. Look up КБЖУ
    lookup = await svc.lookup_product(body.product_name)
    if lookup is None:
        return {"status": "not_found",
                "message": f"Не удалось найти данные для «{body.product_name}». Попробуй другое название."}

    grams = svc.calculate_grams(
        gap_kcal=session["target"]["kcal"] - sum(i["kcal"] for i in session["items"]),
        kcal_per_100g=lookup.kcal,
    )
    factor = grams / 100

    item = {
        "name": lookup.name,
        "grams": grams,
        "kcal": round(lookup.kcal * factor, 1),
        "protein_g": round(lookup.protein_g * factor, 1),
        "fat_g": round(lookup.fat_g * factor, 1),
        "carb_g": round(lookup.carb_g * factor, 1),
        "calcium_mg": round(lookup.calcium_mg * factor, 1),
        "phosphorus_mg": round(lookup.phosphorus_mg * factor, 1),
        "omega3_mg": round(lookup.omega3_mg * factor, 1),
        "taurine_mg": round(lookup.taurine_mg * factor, 1),
    }
    session["items"].append(item)
    await repo.save_session(telegram_id, body.pet_id, session)

    progress = svc.calculate_progress(session["items"], session["target"])
    done = svc.is_done(session["items"], session["target"])

    recommendation = ""
    if not done:
        food_items = await repo.get_all_food_items()
        recommendation = svc.get_recommendation(
            session["items"], session["target"], food_items, pet.species
        )

    return {
        "status": "added",
        "item": item,
        "progress": progress,
        "done": done,
        "recommendation": recommendation,
        "low_confidence": lookup.low_confidence,
        "source": lookup.source,
    }


@router.get("/summary/{pet_id}")
async def get_summary(pet_id: int, request: Request,
                      db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    repo = MealRepository(db)
    session = await repo.get_session(telegram_id, pet_id)
    if not session:
        raise HTTPException(status_code=404, detail={"error": "no_session"})

    svc = MealService(repo)
    breed_risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")
    required_micros = svc.get_required_micros(pet.species, breed_risks)

    totals = svc._sum_items(session["items"])
    target = session["target"]

    ca = totals.get("calcium_mg", 0)
    p  = totals.get("phosphorus_mg", 0)
    ca_p_ratio = round(ca / p, 2) if p > 0 else None

    gaps = {
        k: round(totals.get(k, 0) - v, 1)
        for k, v in target.items()
        if totals.get(k, 0) < v * 0.9
    }
    tip = svc.get_summary_tip(totals, target, required_micros)

    return {
        "items": session["items"],
        "totals": totals,
        "targets": target,
        "ca_p_ratio": ca_p_ratio,
        "gaps": gaps,
        "tip": tip,
        "required_micros": required_micros,
    }


@router.delete("/reset/{pet_id}")
async def reset_session(pet_id: int, request: Request,
                        db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    await MealRepository(db).delete_session(telegram_id, pet_id)
    return {"status": "ok"}


@router.post("/undo-last/{pet_id}")
async def undo_last(pet_id: int, request: Request,
                    db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    updated = await MealRepository(db).undo_last_item(telegram_id, pet_id)
    if updated is None:
        raise HTTPException(status_code=404, detail={"error": "empty_session"})
    return {"status": "ok", "items_count": len(updated.get("items", []))}
```

- [ ] **Step 2: Зарегистрировать роутер в `app/main.py`**

```python
from app.routers import users, pets, nutrition, reminders, ai, weight, breeds, meal
# ...
app.include_router(meal.router, prefix="/v1")
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/meal.py app/main.py
git commit -m "feat: add meal API router (add-product, summary, reset, undo)"
```

---

### Task 9: Bot states + keyboards для MealBuilder

**Files:**
- Modify: `bot/states.py`
- Modify: `bot/keyboards.py`

- [ ] **Step 1: Добавить `MealBuilder` в `bot/states.py`**

```python
from aiogram.fsm.state import State, StatesGroup


class PetCreation(StatesGroup):
    waiting_species        = State()
    waiting_breed          = State()
    waiting_breed_text     = State()
    waiting_breed_photo    = State()
    waiting_breed_suggest  = State()
    waiting_name           = State()
    waiting_age_unit       = State()
    waiting_age            = State()
    waiting_weight         = State()
    waiting_neutered       = State()
    waiting_activity       = State()
    waiting_confirm        = State()


class MealBuilder(StatesGroup):
    waiting_type    = State()
    waiting_product = State()
```

- [ ] **Step 2: Добавить клавиатуры в `bot/keyboards.py`**

Добавить три функции в конец файла:

```python
def meal_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥩 Натуралка",  callback_data="meal_type:natural")],
        [InlineKeyboardButton(text="🥫 Корм",       callback_data="meal_type:prepared")],
        [InlineKeyboardButton(text="🔀 Смешанное",  callback_data="meal_type:mixed")],
        [InlineKeyboardButton(text="← Отмена",      callback_data="meal_cancel")],
    ])


def meal_progress_keyboard(pet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Показать итог",   callback_data=f"meal_summary:{pet_id}")],
        [InlineKeyboardButton(text="↩ Отменить последний", callback_data=f"meal_undo:{pet_id}")],
        [InlineKeyboardButton(text="✖ Начать заново",   callback_data=f"meal_reset:{pet_id}")],
    ])


def meal_l2_keyboard(product_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, добавить",
                              callback_data=f"meal_l2_yes:{product_name}")],
        [InlineKeyboardButton(text="Нет, заменить",
                              callback_data="meal_l2_no")],
    ])
```

- [ ] **Step 3: Commit**

```bash
git add bot/states.py bot/keyboards.py
git commit -m "feat: add MealBuilder states and keyboards"
```

---

### Task 10: Bot handler meal_builder.py

**Files:**
- Create: `bot/handlers/meal_builder.py`
- Modify: `bot/main.py`

- [ ] **Step 1: Создать `bot/handlers/meal_builder.py`**

```python
import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import MealBuilder
from bot.keyboards import (
    meal_type_keyboard, meal_progress_keyboard, meal_l2_keyboard, main_menu_keyboard
)
from app.config import settings

router = Router()

FOOD_TYPE_LABELS = {
    "natural": "🥩 Натуралка",
    "prepared": "🥫 Корм",
    "mixed": "🔀 Смешанное",
}
EXAMPLES = {
    "natural":  "курица, говядина, гречка, морковь, яйцо",
    "prepared": "Royal Canin, Purina Pro Plan, Hills",
    "mixed":    "курица + гречка + сухой корм",
}


# ── Entry points ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("meal_start:"))
async def start_meal_builder(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    await state.update_data(meal_pet_id=pet_id)
    await state.set_state(MealBuilder.waiting_type)
    await callback.message.edit_text(
        "Чем будешь кормить?",
        reply_markup=meal_type_keyboard()
    )


@router.callback_query(F.data == "meal_cancel")
async def cancel_meal(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    await state.set_state(None)
    await callback.message.edit_text("Главное меню", reply_markup=main_menu_keyboard(pet_name))


# ── Type selection ───────────────────────────────────────────────────

@router.callback_query(MealBuilder.waiting_type, F.data.startswith("meal_type:"))
async def choose_food_type(callback: CallbackQuery, state: FSMContext):
    food_type = callback.data.split(":")[1]
    data = await state.get_data()
    pet_id = data.get("meal_pet_id")
    await state.update_data(meal_food_type=food_type)
    await state.set_state(MealBuilder.waiting_product)
    examples = EXAMPLES.get(food_type, "")
    await callback.message.edit_text(
        f"Тип: <b>{FOOD_TYPE_LABELS[food_type]}</b>\n\n"
        f"Вводи продукты по одному.\n"
        f"Примеры: {examples}\n\n"
        "Что добавим первым?",
        parse_mode="HTML",
    )


# ── Product input ────────────────────────────────────────────────────

@router.message(MealBuilder.waiting_product)
async def handle_product_input(message: Message, state: FSMContext):
    data = await state.get_data()
    pet_id = data.get("meal_pet_id")
    food_type = data.get("meal_food_type", "natural")
    telegram_id = message.from_user.id

    await _add_product(message, state, telegram_id, pet_id, food_type,
                       message.text.strip(), force_add=False)


async def _add_product(message_or_cb, state: FSMContext,
                       telegram_id: int, pet_id: int, food_type: str,
                       product_name: str, force_add: bool):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/meal/add-product",
            json={
                "pet_id": pet_id,
                "product_name": product_name,
                "food_type": food_type,
                "force_add": force_add,
            },
            headers={"X-Telegram-Id": str(telegram_id)},
        )

    if resp.status_code != 200:
        text = "Ошибка сервера. Попробуй ещё раз."
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text)
        else:
            await message_or_cb.message.edit_text(text)
        return

    r = resp.json()
    status = r.get("status")

    if status == "blocked":
        text = r["message"]
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, parse_mode="HTML")
        else:
            await message_or_cb.message.edit_text(text, parse_mode="HTML")
        return

    if status == "warning":
        text = r["message"]
        keyboard = meal_l2_keyboard(r["product_name"])
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message_or_cb.message.edit_text(
                text, parse_mode="HTML", reply_markup=keyboard
            )
        return

    if status == "not_found":
        text = r["message"]
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text)
        else:
            await message_or_cb.message.edit_text(text)
        return

    # status == "added"
    item = r["item"]
    progress = r["progress"]
    done = r.get("done", False)
    low_conf = r.get("low_confidence", False)

    conf_note = "\n⚠️ <i>Данные приблизительные — продукт не найден в базе.</i>" if low_conf else ""

    prog_lines = []
    if "kcal_pct" in progress:
        prog_lines.append(f"ккал {int(progress['kcal_pct'])}%")
    if "protein_g_pct" in progress:
        prog_lines.append(f"белок {int(progress['protein_g_pct'])}%")
    if "fat_g_pct" in progress:
        prog_lines.append(f"жир {int(progress['fat_g_pct'])}%")
    prog_str = " · ".join(prog_lines)

    text = (
        f"✅ <b>{item['name']}</b>: {int(item['grams'])}г = {item['kcal']} ккал\n"
        f"📊 {prog_str}{conf_note}"
    )

    if done:
        text += "\n\n<b>Норма закрыта ✅</b>"
    elif r.get("recommendation"):
        text += f"\n💡 {r['recommendation']}"

    if isinstance(message_or_cb, Message):
        await message_or_cb.answer(
            text, parse_mode="HTML",
            reply_markup=meal_progress_keyboard(pet_id)
        )
    else:
        await message_or_cb.message.edit_text(
            text, parse_mode="HTML",
            reply_markup=meal_progress_keyboard(pet_id)
        )


# ── Level 2 confirmation ─────────────────────────────────────────────

@router.callback_query(MealBuilder.waiting_product, F.data.startswith("meal_l2_yes:"))
async def confirm_l2(callback: CallbackQuery, state: FSMContext):
    product_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    pet_id = data.get("meal_pet_id")
    food_type = data.get("meal_food_type", "natural")
    await _add_product(callback, state, callback.from_user.id,
                       pet_id, food_type, product_name, force_add=True)


@router.callback_query(MealBuilder.waiting_product, F.data == "meal_l2_no")
async def skip_l2(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Хорошо, введи другой продукт:")


# ── Summary ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("meal_summary:"))
async def show_summary(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/meal/summary/{pet_id}",
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    if resp.status_code != 200:
        await callback.message.edit_text("Не удалось загрузить итог. Попробуй позже.")
        return
    r = resp.json()

    items_text = "\n".join(
        f"{it['name']} — {int(it['grams'])}г" for it in r["items"]
    )
    sep = "─" * 22
    totals = r["totals"]
    targets = r["targets"]
    required = r.get("required_micros", [])

    def fmt_line(label, key, unit):
        got = totals.get(key, 0)
        tgt = targets.get(key, 0)
        if tgt:
            pct = int(got / tgt * 100)
            icon = "✅" if pct >= 90 else "⚠️"
            return f"{label}: {round(got,1)} / {round(tgt,1)} {unit} ({pct}%) {icon}"
        return f"{label}: {round(got,1)} {unit}"

    lines = [
        f"🍽 <b>Порция (1 кормление)</b>\n",
        items_text,
        sep,
        fmt_line("Энергия", "kcal", "ккал"),
        fmt_line("Белок",   "protein_g", "г"),
        fmt_line("Жир",     "fat_g", "г"),
    ]
    if r.get("ca_p_ratio"):
        ratio = r["ca_p_ratio"]
        icon = "✅" if 1.2 <= ratio <= 1.4 else "⚠️"
        lines.append(f"Ca:P: {ratio}:1 {icon}")
    for micro in required:
        if micro in ("calcium_mg", "phosphorus_mg"):
            continue
        labels = {"omega3_mg": "Омега-3", "taurine_mg": "Таурин"}
        if micro in labels:
            lines.append(fmt_line(labels[micro], micro, "мг"))

    if r.get("tip"):
        lines.append(f"\n💡 {r['tip']}")
    lines.append("\n<i>⚠️ Расчёт приблизительный. Проконсультируйся с ветеринаром.</i>")

    data = await state.get_data()
    pet_name = data.get("active_pet_name", "")
    await state.set_state(None)

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=main_menu_keyboard(pet_name)
    )


# ── Undo / Reset ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("meal_undo:"))
async def undo_last(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/meal/undo-last/{pet_id}",
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    if resp.status_code == 200:
        count = resp.json().get("items_count", 0)
        await callback.answer(f"Последний продукт удалён. Продуктов: {count}")
    else:
        await callback.answer("Нечего отменять.")


@router.callback_query(F.data.startswith("meal_reset:"))
async def reset_meal(callback: CallbackQuery, state: FSMContext):
    pet_id = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{settings.BACKEND_URL}/v1/meal/reset/{pet_id}",
            headers={"X-Telegram-Id": str(telegram_id)},
        )
    data = await state.get_data()
    await state.set_state(MealBuilder.waiting_type)
    await callback.message.edit_text(
        "Начнём заново. Чем будешь кормить?",
        reply_markup=meal_type_keyboard()
    )
```

- [ ] **Step 2: Зарегистрировать роутер в `bot/main.py`**

```python
from bot.handlers import start, pet_creation, nutrition, reminders, ai_handler, weight, meal_builder
# ...
dp.include_router(meal_builder.router)
```

Добавить `dp.include_router(meal_builder.router)` **перед** `start_scheduler(bot)`.

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/meal_builder.py bot/main.py
git commit -m "feat: add MealBuilder bot handler FSM"
```

---

### Task 11: Интеграция входных точек

**Files:**
- Modify: `app/scheduler.py`

- [ ] **Step 1: Обновить `app/scheduler.py` — добавить кнопку в пуш напоминания**

```python
import logging
import ssl
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def _reminder_keyboard(pet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍽 Что дать?",
            callback_data=f"meal_start:{pet_id}"
        )]
    ])


async def check_and_send_reminders():
    if _bot is None:
        return
    now = datetime.now().strftime("%H:%M")
    engine = create_async_engine(settings.async_database_url, connect_args={"ssl": _ssl_ctx})
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        from app.repositories.reminder_repo import ReminderRepository
        from app.repositories.pet_repo import PetRepository
        from app.models.user import User

        reminders = await ReminderRepository(session).get_all_active()
        due = [r for r in reminders if r.time_of_day == now]
        for reminder in due:
            pet = await PetRepository(session).get_by_id(
                pet_id=reminder.pet_id, owner_id=reminder.user_id
            )
            user = await session.get(User, reminder.user_id)
            if pet is None or user is None:
                continue
            try:
                await _bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"Время кормить <b>{pet.name}</b>!\n\nНе забудь про правильную порцию.",
                    parse_mode="HTML",
                    reply_markup=_reminder_keyboard(pet.id),
                )
            except Exception as e:
                logger.warning(f"Reminder send failed for user {user.telegram_id}: {e}")
    await engine.dispose()


def start_scheduler(bot):
    set_bot(bot)
    scheduler.add_job(check_and_send_reminders, "cron", minute="*", id="reminders")
    scheduler.start()
    logger.info("Scheduler started")
```

- [ ] **Step 2: Commit**

```bash
git add app/scheduler.py
git commit -m "feat: add meal_start button to feeding reminder push"
```

---

### Task 12: Финальная проверка

- [ ] **Step 1: Запустить все тесты**

```bash
cd /mnt/c/Users/latys/OneDrive/Рабочий\ стол/Good_idea/pet
pytest tests/ -v
```

Ожидаем: все тесты PASS.

- [ ] **Step 2: Проверить импорты**

```bash
python -c "from app.services.meal_service import MealService; print('ok')"
python -c "from app.routers.meal import router; print('ok')"
python -c "from bot.handlers.meal_builder import router; print('ok')"
```

Каждая команда должна напечатать `ok`.

- [ ] **Step 3: Проверить что миграция применена**

```bash
alembic current
```

Ожидаем: `a1b2c3 (head)`

- [ ] **Step 4: Финальный коммит**

```bash
git add -A
git status  # убедиться что нет лишних файлов
git commit -m "feat: MealBuilder — meal planning with stop-list, КБЖУ + micros"
```
