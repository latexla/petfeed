# Breed Recognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Точное распознавание породы питомца через fuzzy-matching (RapidFuzz) при текстовом вводе и через DeepSeek Vision при вводе фото.

**Architecture:** Новая таблица `breed_registry` + `BreedRepository` (fuzzy-search) + `BreedService` (оркестрация текст/фото) + эндпоинты `GET /v1/breeds` и `POST /v1/breeds/recognize-photo` + обновлённый FSM-шаг породы в боте.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, aiogram 3, RapidFuzz, DeepSeek Vision API (через AsyncOpenAI), Alembic, pytest

---

## Карта файлов

| Действие | Файл | Ответственность |
|---|---|---|
| Создать | `app/models/breed_registry.py` | SQLAlchemy модель |
| Изменить | `app/models/__init__.py` | +BreedRegistry import |
| Создать | `app/repositories/breed_repo.py` | fuzzy_search против реестра |
| Создать | `app/services/breed_service.py` | match_text + recognize_from_photo |
| Создать | `tests/test_breed_service.py` | Unit-тесты BreedService |
| Создать | `alembic/versions/xxxx_breed_registry.py` | Миграция |
| Создать | `app/seeds/breed_seed.py` | ~40 пород RU+EN |
| Создать | `app/routers/breeds.py` | GET /breeds + POST /breeds/recognize-photo |
| Изменить | `app/main.py` | +breeds router |
| Изменить | `requirements.txt` | +rapidfuzz |
| Изменить | `bot/states.py` | +waiting_breed_text, waiting_breed_photo, waiting_breed_suggest |
| Изменить | `bot/keyboards.py` | +breed_method_keyboard, breed_suggestion_keyboard, breed_not_found_keyboard |
| Изменить | `bot/handlers/pet_creation.py` | Обновлённый шаг породы |

---

### Task 1: BreedRegistry модель + RapidFuzz

**Files:**
- Create: `app/models/breed_registry.py`
- Modify: `app/models/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Добавить rapidfuzz в `requirements.txt`**

Добавить строку после `httpx==0.27.2`:
```
rapidfuzz==3.10.0
```

- [ ] **Step 2: Установить пакет**

```bash
pip install rapidfuzz==3.10.0
```

- [ ] **Step 3: Создать `app/models/breed_registry.py`**

```python
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BreedRegistry(Base):
    __tablename__ = "breed_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    aliases: Mapped[list] = mapped_column(ARRAY(String(200)), nullable=False, server_default="{}")
```

- [ ] **Step 4: Обновить `app/models/__init__.py`**

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

__all__ = ["User", "Pet", "FeatureFlag", "Ration", "NutritionKnowledge",
           "FeedingReminder", "AiRequest", "WeightHistory",
           "FoodCategory", "BreedRisk", "StopFood", "BreedRegistry"]
```

- [ ] **Step 5: Синтаксис-проверка**

```bash
python3.12 -c "from app.models.breed_registry import BreedRegistry; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt app/models/breed_registry.py app/models/__init__.py
git commit -m "feat: BreedRegistry model + rapidfuzz dependency"
```

---

### Task 2: Unit-тесты BreedService (TDD — пишем до реализации)

**Files:**
- Create: `tests/test_breed_service.py`

- [ ] **Step 1: Создать `tests/test_breed_service.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.breed_service import BreedService, MatchConfidence
from app.models.breed_registry import BreedRegistry


def make_breed(id, canonical_name, canonical_name_ru, species="dog", aliases=None):
    b = BreedRegistry()
    b.id = id
    b.canonical_name = canonical_name
    b.canonical_name_ru = canonical_name_ru
    b.species = species
    b.aliases = aliases or []
    return b


@pytest.fixture
def jrt():
    return make_breed(1, "Jack Russell Terrier", "Джек Рассел Терьер",
                      aliases=["JRT", "джек расел", "jack russel"])


@pytest.fixture
def labrador():
    return make_breed(2, "Labrador Retriever", "Лабрадор Ретривер",
                      aliases=["лабрадор", "labrador"])


@pytest.mark.asyncio
async def test_high_confidence_exact_match(jrt, labrador):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 100.0), (labrador, 30.0)])
    result = await BreedService(repo).match_text("Jack Russell Terrier", "dog")
    assert result.confidence == MatchConfidence.HIGH
    assert result.candidates[0].canonical_name == "Jack Russell Terrier"


@pytest.mark.asyncio
async def test_medium_confidence_typo(jrt, labrador):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 75.0), (labrador, 45.0)])
    result = await BreedService(repo).match_text("джек расел", "dog")
    assert result.confidence == MatchConfidence.MEDIUM
    assert len(result.candidates) >= 1
    assert result.candidates[0].canonical_name == "Jack Russell Terrier"


@pytest.mark.asyncio
async def test_low_confidence_no_matches():
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[])
    result = await BreedService(repo).match_text("абракадабра", "dog")
    assert result.confidence == MatchConfidence.LOW
    assert result.candidates == []


@pytest.mark.asyncio
async def test_low_confidence_poor_score(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 45.0)])
    result = await BreedService(repo).match_text("zzzzzzz", "dog")
    assert result.confidence == MatchConfidence.LOW


@pytest.mark.asyncio
async def test_raw_input_preserved(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 75.0)])
    result = await BreedService(repo).match_text("джек расел", "dog")
    assert result.raw_input == "джек расел"


@pytest.mark.asyncio
async def test_top_candidates_capped_at_3(jrt, labrador):
    extra = make_breed(3, "Beagle", "Бигль")
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[
        (jrt, 80.0), (labrador, 72.0), (extra, 65.0)
    ])
    result = await BreedService(repo).match_text("query", "dog")
    assert len(result.candidates) <= 3


@pytest.mark.asyncio
async def test_high_threshold_boundary(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 85.0)])
    result = await BreedService(repo).match_text("jack", "dog")
    assert result.confidence == MatchConfidence.HIGH


@pytest.mark.asyncio
async def test_medium_threshold_boundary(jrt):
    repo = MagicMock()
    repo.fuzzy_search = AsyncMock(return_value=[(jrt, 60.0)])
    result = await BreedService(repo).match_text("jack", "dog")
    assert result.confidence == MatchConfidence.MEDIUM
```

- [ ] **Step 2: Запустить — убедиться что падают с ImportError**

```bash
pytest tests/test_breed_service.py -v
```

Ожидаемый вывод: `ImportError: cannot import name 'BreedService'`

- [ ] **Step 3: Commit**

```bash
git add tests/test_breed_service.py
git commit -m "test: BreedService unit tests (failing, TDD)"
```

---

### Task 3: BreedRepository + BreedService

**Files:**
- Create: `app/repositories/breed_repo.py`
- Create: `app/services/breed_service.py`

- [ ] **Step 1: Создать `app/repositories/breed_repo.py`**

```python
from rapidfuzz import process, fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.breed_registry import BreedRegistry


class BreedRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, species: str) -> list[BreedRegistry]:
        result = await self.session.execute(
            select(BreedRegistry).where(BreedRegistry.species == species)
        )
        return list(result.scalars().all())

    async def get_by_id(self, breed_id: int) -> BreedRegistry | None:
        return await self.session.get(BreedRegistry, breed_id)

    async def fuzzy_search(self, query: str, species: str) -> list[tuple[BreedRegistry, float]]:
        breeds = await self.get_all(species)
        if not breeds:
            return []

        corpus: dict[str, int] = {}
        for breed in breeds:
            corpus[breed.canonical_name.lower()] = breed.id
            corpus[breed.canonical_name_ru.lower()] = breed.id
            for alias in (breed.aliases or []):
                corpus[alias.lower()] = breed.id

        results = process.extract(
            query.lower(), list(corpus.keys()), scorer=fuzz.WRatio, limit=10
        )

        best_per_breed: dict[int, float] = {}
        for match_str, score, _ in results:
            breed_id = corpus[match_str]
            if breed_id not in best_per_breed or score > best_per_breed[breed_id]:
                best_per_breed[breed_id] = score

        top = sorted(best_per_breed.items(), key=lambda x: x[1], reverse=True)[:3]
        id_to_breed = {b.id: b for b in breeds}
        return [(id_to_breed[bid], score) for bid, score in top if bid in id_to_breed]
```

- [ ] **Step 2: Создать `app/services/breed_service.py`**

```python
import base64
import logging
from dataclasses import dataclass, field
from enum import Enum

from openai import AsyncOpenAI
from app.config import settings
from app.repositories.breed_repo import BreedRepository

logger = logging.getLogger(__name__)

HIGH_THRESHOLD = 85
MEDIUM_THRESHOLD = 60


class MatchConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BreedCandidate:
    breed_id: int
    canonical_name: str
    canonical_name_ru: str
    score: float


@dataclass
class BreedMatchResult:
    confidence: MatchConfidence
    candidates: list[BreedCandidate]
    raw_input: str


class BreedService:
    def __init__(self, repo: BreedRepository):
        self.repo = repo

    async def match_text(self, text: str, species: str) -> BreedMatchResult:
        matches = await self.repo.fuzzy_search(text, species)
        return self._build_result(matches, text)

    def _build_result(
        self, matches: list, raw_input: str
    ) -> BreedMatchResult:
        if not matches:
            return BreedMatchResult(
                confidence=MatchConfidence.LOW,
                candidates=[],
                raw_input=raw_input,
            )
        top_score = matches[0][1]
        if top_score >= HIGH_THRESHOLD:
            confidence = MatchConfidence.HIGH
        elif top_score >= MEDIUM_THRESHOLD:
            confidence = MatchConfidence.MEDIUM
        else:
            confidence = MatchConfidence.LOW

        candidates = [
            BreedCandidate(
                breed_id=b.id,
                canonical_name=b.canonical_name,
                canonical_name_ru=b.canonical_name_ru,
                score=s,
            )
            for b, s in matches
        ]
        return BreedMatchResult(
            confidence=confidence, candidates=candidates, raw_input=raw_input
        )

    async def recognize_from_photo(
        self, photo_bytes: bytes, species: str
    ) -> BreedMatchResult:
        species_word = "dog" if species == "dog" else "cat"
        b64 = base64.b64encode(photo_bytes).decode()
        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
        try:
            response = await client.chat.completions.create(
                model="deepseek-vl",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}"
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"What breed is this {species_word}? "
                                    "Reply with ONLY the breed name in English, nothing else."
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=50,
            )
            breed_name = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"DeepSeek Vision error: {e}")
            return BreedMatchResult(
                confidence=MatchConfidence.LOW, candidates=[], raw_input=""
            )
        return await self.match_text(breed_name, species)
```

- [ ] **Step 3: Запустить тесты**

```bash
pytest tests/test_breed_service.py -v
```

Ожидаемый вывод: все 8 тестов PASS

- [ ] **Step 4: Commit**

```bash
git add app/repositories/breed_repo.py app/services/breed_service.py
git commit -m "feat: BreedRepository fuzzy search + BreedService"
```

---

### Task 4: Alembic миграция + seed

**Files:**
- Create: `alembic/versions/xxxx_breed_registry.py` (через autogenerate)
- Create: `app/seeds/breed_seed.py`

- [ ] **Step 1: Сгенерировать миграцию**

```bash
alembic revision --autogenerate -m "add_breed_registry"
```

Если нет локальной БД — создать файл вручную. Найти текущий head в `alembic/versions/` (файл `5cbc1aaf70f2_...`). Создать `alembic/versions/<timestamp>_add_breed_registry.py`:

```python
"""add_breed_registry

Revision ID: b3c4d5e6f7a8
Revises: 5cbc1aaf70f2
Create Date: 2026-04-26 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b3c4d5e6f7a8'
down_revision = '5cbc1aaf70f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS breed_registry (
            id SERIAL NOT NULL,
            canonical_name VARCHAR(100) NOT NULL,
            canonical_name_ru VARCHAR(100) NOT NULL,
            species VARCHAR(50) NOT NULL,
            aliases VARCHAR(200)[] NOT NULL DEFAULT '{}',
            PRIMARY KEY (id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_breed_registry_species ON breed_registry(species)")


def downgrade() -> None:
    op.drop_index('idx_breed_registry_species', table_name='breed_registry')
    op.drop_table('breed_registry')
```

- [ ] **Step 2: Применить миграцию на Railway**

```bash
railway run alembic stamp 5cbc1aaf70f2   # если нужно обновить метку
railway run alembic upgrade head
```

Ожидаемый вывод: `Running upgrade 5cbc1aaf70f2 -> b3c4d5e6f7a8, add_breed_registry`

- [ ] **Step 3: Создать `app/seeds/breed_seed.py`**

```python
"""
Seed breeds for dogs and cats.
Run: python3.12 -m app.seeds.breed_seed
"""
import asyncio
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.models.breed_registry import BreedRegistry

BREEDS = [
    # --- DOGS ---
    {"canonical_name": "Jack Russell Terrier", "canonical_name_ru": "Джек Рассел Терьер",
     "species": "dog", "aliases": ["JRT", "джек расел", "jack russel", "джек рассел"]},
    {"canonical_name": "Labrador Retriever", "canonical_name_ru": "Лабрадор Ретривер",
     "species": "dog", "aliases": ["лабрадор", "labrador", "лабр"]},
    {"canonical_name": "German Shepherd", "canonical_name_ru": "Немецкая овчарка",
     "species": "dog", "aliases": ["немецкая", "овчарка", "немец", "немецкая овчарка"]},
    {"canonical_name": "French Bulldog", "canonical_name_ru": "Французский бульдог",
     "species": "dog", "aliases": ["француз", "французский", "бульдог", "фрэнч"]},
    {"canonical_name": "Siberian Husky", "canonical_name_ru": "Сибирский хаски",
     "species": "dog", "aliases": ["хаски", "хасик", "husky"]},
    {"canonical_name": "Golden Retriever", "canonical_name_ru": "Золотистый ретривер",
     "species": "dog", "aliases": ["голден", "золотистый", "ретривер"]},
    {"canonical_name": "Yorkshire Terrier", "canonical_name_ru": "Йоркширский терьер",
     "species": "dog", "aliases": ["йорк", "йорки", "йоркширский"]},
    {"canonical_name": "Chihuahua", "canonical_name_ru": "Чихуахуа",
     "species": "dog", "aliases": ["чиха", "чихуа", "чихуахуа"]},
    {"canonical_name": "Pug", "canonical_name_ru": "Мопс",
     "species": "dog", "aliases": ["мопсик"]},
    {"canonical_name": "Pomeranian", "canonical_name_ru": "Шпиц",
     "species": "dog", "aliases": ["шпиц", "помераниан"]},
    {"canonical_name": "Beagle", "canonical_name_ru": "Бигль",
     "species": "dog", "aliases": ["бигл"]},
    {"canonical_name": "Dobermann", "canonical_name_ru": "Доберман",
     "species": "dog", "aliases": ["доберман"]},
    {"canonical_name": "Rottweiler", "canonical_name_ru": "Ротвейлер",
     "species": "dog", "aliases": ["ротвейлер"]},
    {"canonical_name": "Boxer", "canonical_name_ru": "Боксёр",
     "species": "dog", "aliases": ["боксер"]},
    {"canonical_name": "Dalmatian", "canonical_name_ru": "Далматин",
     "species": "dog", "aliases": ["далматинец", "далматин"]},
    {"canonical_name": "Australian Shepherd", "canonical_name_ru": "Австралийская овчарка",
     "species": "dog", "aliases": ["аусси", "австралийская"]},
    {"canonical_name": "Border Collie", "canonical_name_ru": "Бордер-колли",
     "species": "dog", "aliases": ["бордер", "колли", "бордер колли"]},
    {"canonical_name": "Dachshund", "canonical_name_ru": "Такса",
     "species": "dog", "aliases": ["такса"]},
    {"canonical_name": "Maltese", "canonical_name_ru": "Мальтийская болонка",
     "species": "dog", "aliases": ["мальтез", "мальтийская", "болонка"]},
    {"canonical_name": "Samoyed", "canonical_name_ru": "Самоед",
     "species": "dog", "aliases": ["самоед"]},
    {"canonical_name": "Shih Tzu", "canonical_name_ru": "Ши-тцу",
     "species": "dog", "aliases": ["ши тцу", "ши-тцу"]},
    {"canonical_name": "Poodle", "canonical_name_ru": "Пудель",
     "species": "dog", "aliases": ["пудель"]},
    {"canonical_name": "Corgi", "canonical_name_ru": "Корги",
     "species": "dog", "aliases": ["корги", "вельш-корги", "вельш корги"]},
    {"canonical_name": "English Bulldog", "canonical_name_ru": "Английский бульдог",
     "species": "dog", "aliases": ["английский бульдог", "бульдог"]},
    {"canonical_name": "Alaskan Malamute", "canonical_name_ru": "Аляскинский маламут",
     "species": "dog", "aliases": ["маламут", "аляскинский"]},
    # --- CATS ---
    {"canonical_name": "British Shorthair", "canonical_name_ru": "Британская короткошёрстная",
     "species": "cat", "aliases": ["британец", "британская", "британец кот"]},
    {"canonical_name": "Scottish Fold", "canonical_name_ru": "Шотландская вислоухая",
     "species": "cat", "aliases": ["шотландская", "вислоухая", "скоттиш", "вислоухий"]},
    {"canonical_name": "Maine Coon", "canonical_name_ru": "Мейн-кун",
     "species": "cat", "aliases": ["мейн кун", "мейнкун", "main coon"]},
    {"canonical_name": "Persian", "canonical_name_ru": "Персидская",
     "species": "cat", "aliases": ["перс", "персидский", "персидская"]},
    {"canonical_name": "Bengal", "canonical_name_ru": "Бенгальская",
     "species": "cat", "aliases": ["бенгал", "бенгальский"]},
    {"canonical_name": "Siamese", "canonical_name_ru": "Сиамская",
     "species": "cat", "aliases": ["сиамский", "сиамская"]},
    {"canonical_name": "Sphynx", "canonical_name_ru": "Сфинкс",
     "species": "cat", "aliases": ["сфинкс", "sphinx"]},
    {"canonical_name": "Russian Blue", "canonical_name_ru": "Русская голубая",
     "species": "cat", "aliases": ["русская голубая", "голубая"]},
    {"canonical_name": "Ragdoll", "canonical_name_ru": "Рэгдолл",
     "species": "cat", "aliases": ["рагдол", "рэгдол"]},
    {"canonical_name": "Abyssinian", "canonical_name_ru": "Абиссинская",
     "species": "cat", "aliases": ["абиссинец", "абиссинская"]},
    {"canonical_name": "Norwegian Forest Cat", "canonical_name_ru": "Норвежская лесная",
     "species": "cat", "aliases": ["норвежская", "норвежская лесная"]},
    {"canonical_name": "Burmese", "canonical_name_ru": "Бурманская",
     "species": "cat", "aliases": ["бурма", "бурманская"]},
    {"canonical_name": "Turkish Angora", "canonical_name_ru": "Турецкая ангора",
     "species": "cat", "aliases": ["ангора", "турецкая"]},
    {"canonical_name": "Exotic Shorthair", "canonical_name_ru": "Экзотическая короткошёрстная",
     "species": "cat", "aliases": ["экзот", "экзотик", "экзотическая"]},
    {"canonical_name": "Cornish Rex", "canonical_name_ru": "Корниш-рекс",
     "species": "cat", "aliases": ["корниш", "корниш рекс"]},
]


async def seed():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    engine = create_async_engine(
        settings.async_database_url, connect_args={"ssl": ssl_ctx}
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for data in BREEDS:
            session.add(BreedRegistry(**data))
        await session.commit()
    await engine.dispose()
    print(f"Breed seed complete: {len(BREEDS)} breeds inserted")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 4: Запустить seed на Railway**

```bash
railway run python3.12 -m app.seeds.breed_seed
```

Ожидаемый вывод: `Breed seed complete: 40 breeds inserted`

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/ app/seeds/breed_seed.py
git commit -m "feat: breed_registry migration and seed (40 breeds)"
```

---

### Task 5: API роутер breeds

**Files:**
- Create: `app/routers/breeds.py`
- Modify: `app/main.py`

- [ ] **Step 1: Создать `app/routers/breeds.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.breed_repo import BreedRepository
from app.services.breed_service import BreedService

router = APIRouter(prefix="/breeds", tags=["breeds"])


class BreedCandidateOut(BaseModel):
    breed_id: int
    canonical_name: str
    canonical_name_ru: str
    score: float


class BreedMatchOut(BaseModel):
    confidence: str
    candidates: list[BreedCandidateOut]
    raw_input: str


@router.get("", response_model=BreedMatchOut)
async def search_breeds(species: str, q: str, db: AsyncSession = Depends(get_db)):
    if species not in ("dog", "cat"):
        raise HTTPException(status_code=422, detail="species must be 'dog' or 'cat'")
    service = BreedService(BreedRepository(db))
    result = await service.match_text(q, species)
    return BreedMatchOut(
        confidence=result.confidence,
        candidates=[
            BreedCandidateOut(
                breed_id=c.breed_id,
                canonical_name=c.canonical_name,
                canonical_name_ru=c.canonical_name_ru,
                score=c.score,
            )
            for c in result.candidates
        ],
        raw_input=result.raw_input,
    )


@router.post("/recognize-photo", response_model=BreedMatchOut)
async def recognize_breed_photo(
    species: str = Form(...),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if species not in ("dog", "cat"):
        raise HTTPException(status_code=422, detail="species must be 'dog' or 'cat'")
    photo_bytes = await photo.read()
    service = BreedService(BreedRepository(db))
    result = await service.recognize_from_photo(photo_bytes, species)
    return BreedMatchOut(
        confidence=result.confidence,
        candidates=[
            BreedCandidateOut(
                breed_id=c.breed_id,
                canonical_name=c.canonical_name,
                canonical_name_ru=c.canonical_name_ru,
                score=c.score,
            )
            for c in result.candidates
        ],
        raw_input=result.raw_input,
    )
```

- [ ] **Step 2: Зарегистрировать роутер в `app/main.py`**

Добавить импорт и include_router:

```python
from app.routers import users, pets, nutrition, reminders, ai, weight, breeds
# ...
app.include_router(breeds.router, prefix="/v1")
```

- [ ] **Step 3: Синтаксис-проверка**

```bash
python3.12 -c "from app.routers.breeds import router; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 4: Запустить все тесты**

```bash
pytest tests/ -v
```

Ожидаемый вывод: все тесты PASS (включая 8 новых breed тестов)

- [ ] **Step 5: Commit**

```bash
git add app/routers/breeds.py app/main.py
git commit -m "feat: breeds API router (GET /breeds + POST /breeds/recognize-photo)"
```

---

### Task 6: Bot states + keyboards

**Files:**
- Modify: `bot/states.py`
- Modify: `bot/keyboards.py`

- [ ] **Step 1: Обновить `bot/states.py`**

```python
from aiogram.fsm.state import State, StatesGroup


class PetCreation(StatesGroup):
    waiting_species        = State()
    waiting_breed          = State()   # выбор метода: текст / фото / метис
    waiting_breed_text     = State()   # ввод названия породы
    waiting_breed_photo    = State()   # отправка фото
    waiting_breed_suggest  = State()   # выбор из предложенных вариантов
    waiting_name           = State()
    waiting_age_unit       = State()
    waiting_age            = State()
    waiting_weight         = State()
    waiting_neutered       = State()
    waiting_activity       = State()
    waiting_food_category  = State()
    waiting_confirm        = State()
```

- [ ] **Step 2: Добавить 3 новые клавиатуры в конец `bot/keyboards.py`**

```python
def breed_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать название", callback_data="breed_method:text")],
        [InlineKeyboardButton(text="Отправить фото 📷", callback_data="breed_method:photo")],
        [InlineKeyboardButton(text="Метис / Не знаю", callback_data="breed:unknown")],
    ])


def breed_suggestion_keyboard(candidates: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{c['canonical_name_ru']} ({c['canonical_name']})",
            callback_data=f"breed_pick:{c['breed_id']}"
        )]
        for c in candidates
    ]
    rows.append([InlineKeyboardButton(
        text="Сохранить как введено", callback_data="breed_raw:save"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def breed_not_found_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ввести заново", callback_data="breed_method:text")],
        [InlineKeyboardButton(text="Сохранить как введено", callback_data="breed_raw:save")],
    ])
```

- [ ] **Step 3: Синтаксис-проверка**

```bash
python3.12 -c "from bot.keyboards import breed_method_keyboard, breed_suggestion_keyboard, breed_not_found_keyboard; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 4: Commit**

```bash
git add bot/states.py bot/keyboards.py
git commit -m "feat: breed FSM states and keyboards"
```

---

### Task 7: Обновить обработчик создания питомца

**Files:**
- Modify: `bot/handlers/pet_creation.py`

- [ ] **Step 1: Заменить `bot/handlers/pet_creation.py`** на новую версию целиком:

```python
import httpx
from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import (
    breed_method_keyboard, breed_suggestion_keyboard, breed_not_found_keyboard,
    age_unit_keyboard, confirm_keyboard, main_menu_keyboard, species_keyboard,
    neutered_keyboard, activity_keyboard, food_category_keyboard,
)
from app.config import settings

router = Router()

SPECIES_LABELS = {
    "cat": "Кошка", "dog": "Собака", "rodent": "Грызун",
    "bird": "Птица", "reptile": "Рептилия"
}
ACTIVITY_LABELS = {
    "low": "Низкий", "moderate": "Умеренный",
    "high": "Высокий", "working": "Рабочий"
}


# SCR-02: выбор вида
@router.callback_query(PetCreation.waiting_species, F.data.startswith("species:"))
async def process_species(callback: CallbackQuery, state: FSMContext):
    species = callback.data.split(":")[1]
    await state.update_data(species=species)
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 9\nКакая порода?",
        reply_markup=breed_method_keyboard()
    )


# SCR-03: выбор метода ввода породы
@router.callback_query(PetCreation.waiting_breed, F.data == "breed_method:text")
async def breed_choose_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed_text)
    await callback.message.edit_text("Напиши название породы:")


@router.callback_query(PetCreation.waiting_breed, F.data == "breed_method:photo")
async def breed_choose_photo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed_photo)
    await callback.message.edit_text("Отправь фото питомца 📷")


@router.callback_query(
    F.data == "breed:unknown",
    PetCreation.waiting_breed
)
async def process_breed_unknown(callback: CallbackQuery, state: FSMContext):
    await state.update_data(breed=None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 9\nКак зовут питомца?")


# SCR-03a: ввод названия породы текстом
@router.message(PetCreation.waiting_breed_text)
async def process_breed_text_input(message: Message, state: FSMContext):
    data = await state.get_data()
    species = data.get("species", "dog")
    query = message.text.strip()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/breeds",
            params={"species": species, "q": query},
            headers={"X-Telegram-Id": str(message.from_user.id)},
        )

    if resp.status_code != 200:
        await message.answer("Ошибка поиска породы. Попробуй ещё раз.")
        return

    await _handle_breed_result(message, state, resp.json())


# SCR-03b: отправка фото для распознавания породы
@router.message(PetCreation.waiting_breed_photo, F.photo)
async def process_breed_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    species = data.get("species", "dog")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buf = BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    photo_bytes = buf.getvalue()

    await message.answer("Распознаю породу... ⏳")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/breeds/recognize-photo",
            data={"species": species},
            files={"photo": ("photo.jpg", photo_bytes, "image/jpeg")},
            headers={"X-Telegram-Id": str(message.from_user.id)},
        )

    if resp.status_code != 200:
        await message.answer(
            "Не удалось распознать породу по фото. Попробуй написать название.",
            reply_markup=breed_method_keyboard()
        )
        await state.set_state(PetCreation.waiting_breed)
        return

    await _handle_breed_result(message, state, resp.json())


# Нет фото — напоминаем
@router.message(PetCreation.waiting_breed_photo)
async def process_breed_photo_not_photo(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправь именно фото 📷")


async def _handle_breed_result(message: Message, state: FSMContext, result: dict):
    confidence = result["confidence"]
    candidates = result["candidates"]
    raw_input = result["raw_input"]

    if confidence == "high":
        breed_name = candidates[0]["canonical_name_ru"]
        await state.update_data(breed=breed_name)
        await state.set_state(PetCreation.waiting_name)
        await message.answer("Шаг 3 из 9\nКак зовут питомца?")

    elif confidence == "medium":
        await state.update_data(pending_breed_input=raw_input)
        await state.set_state(PetCreation.waiting_breed_suggest)
        await message.answer(
            "Уточни породу — выбери из вариантов:",
            reply_markup=breed_suggestion_keyboard(candidates)
        )

    else:  # low
        await state.update_data(pending_breed_input=raw_input)
        await state.set_state(PetCreation.waiting_breed_suggest)
        await message.answer(
            f"Порода «{raw_input}» не найдена в реестре. Что сделать?",
            reply_markup=breed_not_found_keyboard()
        )


# SCR-03c: пользователь выбирает породу из предложенных
@router.callback_query(PetCreation.waiting_breed_suggest, F.data.startswith("breed_pick:"))
async def process_breed_pick(callback: CallbackQuery, state: FSMContext):
    breed_id = int(callback.data.split(":")[1])
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/breeds",
            params={"species": "dog", "q": f"id:{breed_id}"},
            headers={"X-Telegram-Id": str(callback.from_user.id)},
        )
    # Используем canonical_name_ru из callback — он уже был в тексте кнопки
    # Достаём из FSM данных candidates, сохранённых при показе клавиатуры
    # Более надёжно: хранить candidates в FSM state
    data = await state.get_data()
    # candidates хранятся в pending_breed_candidates
    candidates = data.get("pending_breed_candidates", [])
    match = next((c for c in candidates if c["breed_id"] == breed_id), None)
    if match:
        breed_name = match["canonical_name_ru"]
    else:
        breed_name = str(breed_id)

    await state.update_data(breed=breed_name)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 9\nКак зовут питомца?")


# SCR-03d: сохранить как введено
@router.callback_query(PetCreation.waiting_breed_suggest, F.data == "breed_raw:save")
async def process_breed_raw_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    raw = data.get("pending_breed_input", "")
    await state.update_data(breed=raw if raw else None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 9\nКак зовут питомца?")


# SCR-03e: ввести заново (из экрана "не найдено")
@router.callback_query(PetCreation.waiting_breed_suggest, F.data == "breed_method:text")
async def process_breed_retry(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_breed_text)
    await callback.message.edit_text("Напиши название породы:")


# SCR-04: ввод имени
@router.message(PetCreation.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PetCreation.waiting_age_unit)
    await message.answer(
        "Шаг 4 из 9\nСколько питомцу?",
        reply_markup=age_unit_keyboard()
    )


# SCR-05а: выбор единицы возраста
@router.callback_query(PetCreation.waiting_age_unit, F.data.startswith("age_unit:"))
async def process_age_unit(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.split(":")[1]
    await state.update_data(age_unit=unit)
    await state.set_state(PetCreation.waiting_age)
    if unit == "months":
        await callback.message.edit_text("Введи возраст в месяцах:\n\nНапример: 6, 24, 36")
    else:
        await callback.message.edit_text("Введи возраст в годах:\n\nНапример: 1, 3, 7")


# SCR-05б: ввод числа возраста
@router.message(PetCreation.waiting_age)
async def process_age(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        data = await state.get_data()
        unit_label = "месяцев" if data.get("age_unit") == "months" else "лет"
        await message.answer(f"Введи целое положительное число ({unit_label}). Например: 3")
        return

    value = int(text)
    data = await state.get_data()
    unit = data.get("age_unit", "months")

    if unit == "years":
        age_months = value * 12
        age_display = f"{value} {'год' if value == 1 else 'года' if 2 <= value <= 4 else 'лет'} ({age_months} мес)"
    else:
        age_months = value
        age_display = f"{age_months} мес"

    await state.update_data(age_months=age_months, age_display=age_display)
    await state.set_state(PetCreation.waiting_weight)
    await message.answer("Шаг 6 из 9\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2")


# SCR-06: ввод веса → кастрация или активность
@router.message(PetCreation.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.strip().replace(",", "."))
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи вес в кг. Например: 5.2")
        return
    await state.update_data(weight_kg=weight)
    data = await state.get_data()
    age_months = data.get("age_months", 0)

    if age_months >= 12:
        await state.set_state(PetCreation.waiting_neutered)
        await message.answer(
            "Шаг 7 из 9\nПитомец кастрирован / стерилизован?",
            reply_markup=neutered_keyboard()
        )
    else:
        await state.update_data(is_neutered=False)
        await state.set_state(PetCreation.waiting_activity)
        await message.answer(
            "Шаг 7 из 9\nУровень активности питомца?",
            reply_markup=activity_keyboard()
        )


# SCR-06a: статус кастрации
@router.callback_query(PetCreation.waiting_neutered, F.data.startswith("neutered:"))
async def process_neutered(callback: CallbackQuery, state: FSMContext):
    is_neutered = callback.data.split(":")[1] == "yes"
    await state.update_data(is_neutered=is_neutered)
    await state.set_state(PetCreation.waiting_activity)
    await callback.message.edit_text(
        "Шаг 8 из 9\nУровень активности питомца?",
        reply_markup=activity_keyboard()
    )


# SCR-07: уровень активности
@router.callback_query(PetCreation.waiting_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split(":")[1]
    await state.update_data(activity_level=activity)
    await state.set_state(PetCreation.waiting_food_category)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/nutrition/food-categories",
            headers={"X-Telegram-Id": str(callback.from_user.id)}
        )
    if resp.status_code == 200:
        categories = resp.json()
    else:
        categories = [
            {"id": 1, "name": "Сухой корм", "kcal_per_100g": 350},
            {"id": 2, "name": "Влажный корм", "kcal_per_100g": 85},
            {"id": 3, "name": "Натуральный", "kcal_per_100g": 150},
            {"id": 4, "name": "BARF (сырое)", "kcal_per_100g": 130},
        ]
    await callback.message.edit_text(
        "Шаг 9 из 9\nЧем кормите питомца?",
        reply_markup=food_category_keyboard(categories)
    )


# SCR-08: тип корма → подтверждение
@router.callback_query(PetCreation.waiting_food_category, F.data.startswith("food_cat:"))
async def process_food_category(callback: CallbackQuery, state: FSMContext):
    food_category_id = int(callback.data.split(":")[1])
    await state.update_data(food_category_id=food_category_id)
    data = await state.get_data()

    breed_label = data.get("breed") or "Метис"
    neutered_label = "Да" if data.get("is_neutered") else "Нет"
    activity_label = ACTIVITY_LABELS.get(data.get("activity_level", "moderate"), "Умеренный")

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


# SCR-09: подтверждение — сохранить
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
                "food_category_id": data.get("food_category_id"),
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


# SCR-09: подтверждение — изменить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_species)
    await callback.message.edit_text(
        "Шаг 1 из 9\nКто твой питомец?",
        reply_markup=species_keyboard()
    )
```

**ВАЖНО:** В `process_breed_pick` нужно хранить candidates в FSM. Обновить `_handle_breed_result`:

```python
async def _handle_breed_result(message: Message, state: FSMContext, result: dict):
    confidence = result["confidence"]
    candidates = result["candidates"]
    raw_input = result["raw_input"]

    if confidence == "high":
        breed_name = candidates[0]["canonical_name_ru"]
        await state.update_data(breed=breed_name)
        await state.set_state(PetCreation.waiting_name)
        await message.answer("Шаг 3 из 9\nКак зовут питомца?")

    elif confidence == "medium":
        await state.update_data(pending_breed_input=raw_input, pending_breed_candidates=candidates)
        await state.set_state(PetCreation.waiting_breed_suggest)
        await message.answer(
            "Уточни породу — выбери из вариантов:",
            reply_markup=breed_suggestion_keyboard(candidates)
        )

    else:
        await state.update_data(pending_breed_input=raw_input, pending_breed_candidates=[])
        await state.set_state(PetCreation.waiting_breed_suggest)
        await message.answer(
            f"Порода «{raw_input}» не найдена в реестре. Что сделать?",
            reply_markup=breed_not_found_keyboard()
        )
```

- [ ] **Step 2: Синтаксис-проверка**

```bash
python3.12 -c "from bot.handlers.pet_creation import router; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 3: Запустить все тесты**

```bash
pytest tests/ -v
```

Ожидаемый вывод: все тесты PASS

- [ ] **Step 4: Commit**

```bash
git add bot/handlers/pet_creation.py
git commit -m "feat: breed recognition in pet creation FSM (text + photo)"
```

---

### Task 8: Push + деплой

- [ ] **Step 1: Применить миграцию на Railway (если ещё не)**

```bash
railway run alembic upgrade head
```

- [ ] **Step 2: Запустить seed**

```bash
railway run python3.12 -m app.seeds.breed_seed
```

- [ ] **Step 3: Push**

```bash
git push
```

- [ ] **Step 4: Проверить в боте**
  - Создать нового питомца (собаку)
  - На шаге породы: написать "джек расел" → должен предложить "Джек Рассел Терьер"
  - На шаге породы: написать точно "Labrador Retriever" → должен принять без вопросов
  - На шаге породы: написать полную ерунду → должен показать "не найдено"
  - На шаге породы: нажать "Отправить фото" → отправить фото → получить распознавание
