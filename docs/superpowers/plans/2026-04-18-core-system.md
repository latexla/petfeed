# Core System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Поднять ядро PetFeed — FastAPI backend + PostgreSQL + Redis + Telegram Bot (aiogram 3) + FSM онбординга (SCR-01..SCR-07).

**Architecture:** Трёхслойная архитектура (Router → Service → Repository). Bot общается с Backend через HTTP. FSM-состояния диалога хранятся в Redis.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, aiogram 3, pydantic-settings, asyncpg, redis-py, pytest, pytest-asyncio

---

## Структура файлов

```
app/
├── __init__.py
├── main.py                  ← FastAPI приложение
├── config.py                ← Настройки (pydantic-settings)
├── database.py              ← SQLAlchemy async engine + session
├── redis_client.py          ← Redis connection
├── models/
│   ├── __init__.py
│   ├── user.py              ← ORM модель User
│   ├── pet.py               ← ORM модель Pet
│   └── feature_flag.py      ← ORM модель FeatureFlag
├── schemas/
│   ├── __init__.py
│   ├── user.py              ← Pydantic схемы User
│   └── pet.py               ← Pydantic схемы Pet
├── repositories/
│   ├── __init__.py
│   ├── user_repo.py         ← CRUD для users
│   └── pet_repo.py          ← CRUD для pets
├── services/
│   ├── __init__.py
│   ├── user_service.py      ← Бизнес-логика пользователей
│   ├── pet_service.py       ← Бизнес-логика питомцев (BL-001)
│   └── feature_flag_service.py ← Проверка флагов
├── routers/
│   ├── __init__.py
│   ├── users.py             ← GET /users/me
│   └── pets.py              ← POST/GET /pets, GET/PUT /pets/{id}
└── middleware/
    ├── __init__.py
    └── auth.py              ← Проверка X-Telegram-Id

bot/
├── __init__.py
├── main.py                  ← Запуск бота
├── states.py                ← FSM StatesGroup
├── keyboards.py             ← Inline-клавиатуры
└── handlers/
    ├── __init__.py
    ├── start.py             ← /start, SCR-01
    └── pet_creation.py      ← FSM онбординг, SCR-02..07

tests/
├── __init__.py
├── conftest.py              ← Fixtures: test DB, test client
├── test_user_service.py
├── test_pet_service.py
└── test_pet_router.py

alembic/
├── env.py
└── versions/
    └── 001_initial_schema.py

alembic.ini
requirements.txt
.env.example
docker-compose.yml
```

---

## Task 1: Структура проекта и зависимости

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `app/__init__.py`, `app/models/__init__.py`, `app/schemas/__init__.py`
- Create: `app/repositories/__init__.py`, `app/services/__init__.py`
- Create: `app/routers/__init__.py`, `app/middleware/__init__.py`
- Create: `bot/__init__.py`, `bot/handlers/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Создать файл зависимостей**

```
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.29.0
alembic==1.13.3
pydantic-settings==2.5.2
pydantic[email]==2.9.0
aiogram==3.13.0
redis[asyncio]==5.1.1
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
```

- [ ] **Step 2: Создать `.env.example`**

```ini
# .env.example
DATABASE_URL=postgresql+asyncpg://petfeed:petfeed@localhost:5432/petfeed
REDIS_URL=redis://localhost:6379/0
TELEGRAM_BOT_TOKEN=your_bot_token_here
BACKEND_URL=http://localhost:8000
ADMIN_TOKEN=change_me_in_production
DEEPSEEK_API_KEY=your_deepseek_key_here
```

- [ ] **Step 3: Создать `docker-compose.yml`**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: petfeed
      POSTGRES_PASSWORD: petfeed
      POSTGRES_DB: petfeed
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

- [ ] **Step 4: Создать пустые `__init__.py` во всех папках**

```bash
mkdir -p app/models app/schemas app/repositories app/services app/routers app/middleware
mkdir -p bot/handlers tests alembic/versions
touch app/__init__.py app/models/__init__.py app/schemas/__init__.py
touch app/repositories/__init__.py app/services/__init__.py
touch app/routers/__init__.py app/middleware/__init__.py
touch bot/__init__.py bot/handlers/__init__.py
touch tests/__init__.py
```

- [ ] **Step 5: Установить зависимости и поднять инфраструктуру**

```bash
pip install -r requirements.txt
docker-compose up -d
docker-compose ps  # db и redis должны быть Up
```

- [ ] **Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: initial project structure and dependencies"
```

---

## Task 2: Config + Database + Redis

**Files:**
- Create: `app/config.py`
- Create: `app/database.py`
- Create: `app/redis_client.py`

- [ ] **Step 1: Написать тест конфига**

```python
# tests/test_config.py
from app.config import settings

def test_settings_loaded():
    assert settings.DATABASE_URL is not None
    assert settings.REDIS_URL is not None
    assert settings.TELEGRAM_BOT_TOKEN is not None
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_config.py -v
# Expected: FAIL — ModuleNotFoundError
```

- [ ] **Step 3: Создать `app/config.py`**

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    TELEGRAM_BOT_TOKEN: str
    BACKEND_URL: str = "http://localhost:8000"
    ADMIN_TOKEN: str = "change_me"
    DEEPSEEK_API_KEY: str = ""
    AI_DAILY_LIMIT: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

- [ ] **Step 4: Создать `.env` из `.env.example` и заполнить**

```bash
cp .env.example .env
# Заполнить реальными значениями TELEGRAM_BOT_TOKEN
```

- [ ] **Step 5: Создать `app/database.py`**

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 6: Создать `app/redis_client.py`**

```python
# app/redis_client.py
import redis.asyncio as redis
from app.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)
```

- [ ] **Step 7: Запустить тест конфига — убедиться что проходит**

```bash
pytest tests/test_config.py -v
# Expected: PASS
```

- [ ] **Step 8: Commit**

```bash
git add app/config.py app/database.py app/redis_client.py tests/test_config.py .env.example
git commit -m "feat: add config, database and redis client"
```

---

## Task 3: SQLAlchemy модели

**Files:**
- Create: `app/models/user.py`
- Create: `app/models/pet.py`
- Create: `app/models/feature_flag.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Написать тест моделей**

```python
# tests/test_models.py
from app.models.user import User
from app.models.pet import Pet
from app.models.feature_flag import FeatureFlag

def test_user_model_has_required_fields():
    u = User(telegram_id=123, username="test")
    assert u.telegram_id == 123
    assert u.is_active == True
    assert u.ai_requests_today == 0

def test_pet_model_has_required_fields():
    p = Pet(owner_id=1, name="Барсик", species="cat", age_months=24, weight_kg=5.2, goal="maintain")
    assert p.name == "Барсик"
    assert p.is_active == True

def test_feature_flag_model():
    f = FeatureFlag(key="feature_nutrition", name="Питание", is_enabled=True)
    assert f.key == "feature_nutrition"
```

- [ ] **Step 2: Запустить — убедиться что падает**

```bash
pytest tests/test_models.py -v
# Expected: FAIL
```

- [ ] **Step 3: Создать `app/models/user.py`**

```python
# app/models/user.py
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_requests_today: Mapped[int] = mapped_column(Integer, default=0)
    ai_requests_reset_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: Создать `app/models/pet.py`**

```python
# app/models/pet.py
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, Numeric, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint("age_months >= 0", name="ck_pets_age"),
        CheckConstraint("weight_kg > 0", name="ck_pets_weight"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), default="maintain")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 5: Создать `app/models/feature_flag.py`**

```python
# app/models/feature_flag.py
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 6: Обновить `app/models/__init__.py`**

```python
# app/models/__init__.py
from app.models.user import User
from app.models.pet import Pet
from app.models.feature_flag import FeatureFlag

__all__ = ["User", "Pet", "FeatureFlag"]
```

- [ ] **Step 7: Запустить тесты — убедиться что проходят**

```bash
pytest tests/test_models.py -v
# Expected: PASS
```

- [ ] **Step 8: Commit**

```bash
git add app/models/ tests/test_models.py
git commit -m "feat: add SQLAlchemy models for User, Pet, FeatureFlag"
```

---

## Task 4: Alembic миграции

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/001_initial_schema.py`

- [ ] **Step 1: Инициализировать Alembic**

```bash
alembic init alembic
```

- [ ] **Step 2: Обновить `alembic/env.py`**

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — регистрирует все модели

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3: Сгенерировать первую миграцию**

```bash
alembic revision --autogenerate -m "initial_schema"
# Проверить созданный файл в alembic/versions/
```

- [ ] **Step 4: Применить миграцию**

```bash
alembic upgrade head
# Expected: таблицы созданы в PostgreSQL
```

- [ ] **Step 5: Проверить таблицы в БД**

```bash
docker exec -it $(docker-compose ps -q db) psql -U petfeed -d petfeed -c "\dt"
# Expected: users, pets, feature_flags
```

- [ ] **Step 6: Commit**

```bash
git add alembic/ alembic.ini
git commit -m "feat: add alembic migrations with initial schema"
```

---

## Task 5: User Repository и Service

**Files:**
- Create: `app/repositories/user_repo.py`
- Create: `app/services/user_service.py`
- Create: `app/schemas/user.py`
- Create: `tests/conftest.py`
- Create: `tests/test_user_service.py`

- [ ] **Step 1: Создать `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base

TEST_DB_URL = "postgresql+asyncpg://petfeed:petfeed@localhost:5432/petfeed_test"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 2: Написать тесты user service**

```python
# tests/test_user_service.py
import pytest
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository

@pytest.mark.asyncio
async def test_get_or_create_user_creates_new(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    user = await service.get_or_create(telegram_id=123456, username="testuser")
    assert user.id is not None
    assert user.telegram_id == 123456
    assert user.username == "testuser"
    assert user.ai_requests_today == 0

@pytest.mark.asyncio
async def test_get_or_create_user_returns_existing(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    user1 = await service.get_or_create(telegram_id=111, username="user1")
    user2 = await service.get_or_create(telegram_id=111, username="user1")
    assert user1.id == user2.id

@pytest.mark.asyncio
async def test_get_by_telegram_id(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    await service.get_or_create(telegram_id=999, username="findme")
    user = await service.get_by_telegram_id(999)
    assert user is not None
    assert user.username == "findme"
```

- [ ] **Step 3: Запустить — убедиться что падает**

```bash
pytest tests/test_user_service.py -v
# Expected: FAIL — ModuleNotFoundError
```

- [ ] **Step 4: Создать `app/repositories/user_repo.py`**

```python
# app/repositories/user_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(self, telegram_id: int, username: str | None) -> User:
        user = User(telegram_id=telegram_id, username=username)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
```

- [ ] **Step 5: Создать `app/services/user_service.py`**

```python
# app/services/user_service.py
from app.models.user import User
from app.repositories.user_repo import UserRepository

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> User:
        user = await self.repo.get_by_telegram_id(telegram_id)
        if user is None:
            user = await self.repo.create(telegram_id=telegram_id, username=username)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.repo.get_by_telegram_id(telegram_id)
```

- [ ] **Step 6: Создать `app/schemas/user.py`**

```python
# app/schemas/user.py
from datetime import datetime
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    is_active: bool
    ai_requests_today: int
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 7: Создать тестовую БД и запустить тесты**

```bash
docker exec -it $(docker-compose ps -q db) psql -U petfeed -c "CREATE DATABASE petfeed_test;"
pytest tests/test_user_service.py -v
# Expected: PASS (3 tests)
```

- [ ] **Step 8: Commit**

```bash
git add app/repositories/user_repo.py app/services/user_service.py app/schemas/user.py tests/
git commit -m "feat: add User repository, service and schemas"
```

---

## Task 6: Pet Repository и Service (BL-001)

**Files:**
- Create: `app/repositories/pet_repo.py`
- Create: `app/services/pet_service.py`
- Create: `app/schemas/pet.py`
- Create: `tests/test_pet_service.py`

- [ ] **Step 1: Написать тесты pet service**

```python
# tests/test_pet_service.py
import pytest
from app.services.pet_service import PetService
from app.services.user_service import UserService
from app.repositories.pet_repo import PetRepository
from app.repositories.user_repo import UserRepository

@pytest.mark.asyncio
async def test_create_pet(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=1, username="u")
    service = PetService(PetRepository(db_session))
    pet = await service.create(
        owner_id=user.id, name="Барсик", species="cat",
        breed="Мейн-кун", age_months=24, weight_kg=5.2, goal="maintain"
    )
    assert pet.id is not None
    assert pet.name == "Барсик"
    assert pet.species == "cat"

@pytest.mark.asyncio
async def test_get_pet_by_owner(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=2, username="u2")
    service = PetService(PetRepository(db_session))
    await service.create(owner_id=user.id, name="Рекс", species="dog",
                         age_months=36, weight_kg=28.5, goal="lose")
    pets = await service.get_by_owner(user.id)
    assert len(pets) == 1
    assert pets[0].name == "Рекс"

@pytest.mark.asyncio
async def test_get_pet_wrong_owner_returns_none(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=3, username="u3")
    service = PetService(PetRepository(db_session))
    pet = await service.create(owner_id=user.id, name="Пушок", species="rodent",
                               age_months=12, weight_kg=0.5, goal="maintain")
    result = await service.get_by_id(pet_id=pet.id, owner_id=999)
    assert result is None

@pytest.mark.asyncio
async def test_invalid_species_raises_error(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=4, username="u4")
    service = PetService(PetRepository(db_session))
    with pytest.raises(ValueError, match="invalid_species"):
        await service.create(owner_id=user.id, name="X", species="dragon",
                             age_months=1, weight_kg=1.0, goal="maintain")
```

- [ ] **Step 2: Запустить — убедиться что падает**

```bash
pytest tests/test_pet_service.py -v
# Expected: FAIL
```

- [ ] **Step 3: Создать `app/repositories/pet_repo.py`**

```python
# app/repositories/pet_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pet import Pet

class PetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Pet:
        pet = Pet(**kwargs)
        self.session.add(pet)
        await self.session.commit()
        await self.session.refresh(pet)
        return pet

    async def get_by_owner(self, owner_id: int) -> list[Pet]:
        result = await self.session.execute(
            select(Pet).where(Pet.owner_id == owner_id, Pet.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_id(self, pet_id: int, owner_id: int) -> Pet | None:
        result = await self.session.execute(
            select(Pet).where(Pet.id == pet_id, Pet.owner_id == owner_id, Pet.is_active == True)
        )
        return result.scalar_one_or_none()

    async def update(self, pet: Pet, **kwargs) -> Pet:
        for key, value in kwargs.items():
            setattr(pet, key, value)
        await self.session.commit()
        await self.session.refresh(pet)
        return pet
```

- [ ] **Step 4: Создать `app/services/pet_service.py`**

```python
# app/services/pet_service.py
from app.models.pet import Pet
from app.repositories.pet_repo import PetRepository

ALLOWED_SPECIES = {"cat", "dog", "rodent", "bird", "reptile"}
ALLOWED_GOALS = {"maintain", "lose", "gain", "growth"}

class PetService:
    def __init__(self, repo: PetRepository):
        self.repo = repo

    async def create(self, owner_id: int, name: str, species: str,
                     age_months: int, weight_kg: float, goal: str = "maintain",
                     breed: str | None = None) -> Pet:
        if species not in ALLOWED_SPECIES:
            raise ValueError(f"invalid_species: {species}. Allowed: {ALLOWED_SPECIES}")
        if goal not in ALLOWED_GOALS:
            raise ValueError(f"invalid_goal: {goal}. Allowed: {ALLOWED_GOALS}")
        if age_months < 0:
            raise ValueError("invalid_age: age_months must be >= 0")
        if weight_kg <= 0:
            raise ValueError("invalid_weight: weight_kg must be > 0")
        if goal == "growth" and age_months >= 18:
            raise ValueError("invalid_goal: growth is only for animals under 18 months")
        return await self.repo.create(
            owner_id=owner_id, name=name, species=species, breed=breed,
            age_months=age_months, weight_kg=weight_kg, goal=goal
        )

    async def get_by_owner(self, owner_id: int) -> list[Pet]:
        return await self.repo.get_by_owner(owner_id)

    async def get_by_id(self, pet_id: int, owner_id: int) -> Pet | None:
        return await self.repo.get_by_id(pet_id=pet_id, owner_id=owner_id)

    async def update(self, pet_id: int, owner_id: int, **kwargs) -> Pet | None:
        pet = await self.repo.get_by_id(pet_id=pet_id, owner_id=owner_id)
        if pet is None:
            return None
        if "species" in kwargs and kwargs["species"] not in ALLOWED_SPECIES:
            raise ValueError(f"invalid_species")
        return await self.repo.update(pet, **kwargs)
```

- [ ] **Step 5: Создать `app/schemas/pet.py`**

```python
# app/schemas/pet.py
from datetime import datetime
from pydantic import BaseModel, field_validator

ALLOWED_SPECIES = ["cat", "dog", "rodent", "bird", "reptile"]
ALLOWED_GOALS = ["maintain", "lose", "gain", "growth"]

class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None = None
    age_months: int
    weight_kg: float
    goal: str = "maintain"

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

class PetUpdate(BaseModel):
    name: str | None = None
    breed: str | None = None
    age_months: int | None = None
    weight_kg: float | None = None
    goal: str | None = None

class PetResponse(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None
    age_months: int
    weight_kg: float
    goal: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Запустить тесты — убедиться что проходят**

```bash
pytest tests/test_pet_service.py -v
# Expected: PASS (4 tests)
```

- [ ] **Step 7: Commit**

```bash
git add app/repositories/pet_repo.py app/services/pet_service.py app/schemas/pet.py tests/test_pet_service.py
git commit -m "feat: add Pet repository, service and schemas with BL-001 validation"
```

---

## Task 7: FastAPI приложение + роутеры

**Files:**
- Create: `app/middleware/auth.py`
- Create: `app/routers/users.py`
- Create: `app/routers/pets.py`
- Create: `app/main.py`
- Create: `tests/test_pet_router.py`

- [ ] **Step 1: Написать тесты роутера**

```python
# tests/test_pet_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_pet_success(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/pets", json={
            "name": "Барсик", "species": "cat", "breed": "Мейн-кун",
            "age_months": 24, "weight_kg": 5.2, "goal": "maintain"
        }, headers={"X-Telegram-Id": "123456789"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Барсик"
    assert data["species"] == "cat"

@pytest.mark.asyncio
async def test_create_pet_invalid_species(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/pets", json={
            "name": "Дракон", "species": "dragon",
            "age_months": 1, "weight_kg": 1.0
        }, headers={"X-Telegram-Id": "123456789"})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_get_pets_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/pets")
    assert response.status_code == 401
```

- [ ] **Step 2: Создать `app/middleware/auth.py`**

```python
# app/middleware/auth.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def telegram_auth_middleware(request: Request, call_next):
    public_paths = ["/docs", "/openapi.json", "/health", "/v1/orders/webhook"]
    if any(request.url.path.startswith(p) for p in public_paths):
        return await call_next(request)

    telegram_id = request.headers.get("X-Telegram-Id")
    if not telegram_id or not telegram_id.isdigit():
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "X-Telegram-Id header required"}
        )
    request.state.telegram_id = int(telegram_id)
    return await call_next(request)
```

- [ ] **Step 3: Создать `app/routers/users.py`**

```python
# app/routers/users.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    service = UserService(UserRepository(db))
    user = await service.get_or_create(telegram_id=telegram_id)
    return user
```

- [ ] **Step 4: Создать `app/routers/pets.py`**

```python
# app/routers/pets.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.schemas.pet import PetCreate, PetUpdate, PetResponse

router = APIRouter(prefix="/pets", tags=["pets"])

async def get_or_create_user(request: Request, db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    user_service = UserService(UserRepository(db))
    return await user_service.get_or_create(telegram_id=telegram_id)

@router.post("", response_model=PetResponse, status_code=201)
async def create_pet(data: PetCreate, db: AsyncSession = Depends(get_db),
                     request: Request = None):
    user = await get_or_create_user(request, db)
    existing = await PetService(PetRepository(db)).get_by_owner(user.id)
    if existing:
        raise HTTPException(status_code=409, detail={"error": "pet_already_exists"})
    try:
        pet = await PetService(PetRepository(db)).create(
            owner_id=user.id, **data.model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    return pet

@router.get("", response_model=list[PetResponse])
async def get_pets(db: AsyncSession = Depends(get_db), request: Request = None):
    user = await get_or_create_user(request, db)
    return await PetService(PetRepository(db)).get_by_owner(user.id)

@router.get("/{pet_id}", response_model=PetResponse)
async def get_pet(pet_id: int, db: AsyncSession = Depends(get_db), request: Request = None):
    user = await get_or_create_user(request, db)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return pet

@router.put("/{pet_id}", response_model=PetResponse)
async def update_pet(pet_id: int, data: PetUpdate, db: AsyncSession = Depends(get_db),
                     request: Request = None):
    user = await get_or_create_user(request, db)
    pet = await PetService(PetRepository(db)).update(
        pet_id=pet_id, owner_id=user.id,
        **{k: v for k, v in data.model_dump().items() if v is not None}
    )
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return pet
```

- [ ] **Step 5: Создать `app/main.py`**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import telegram_auth_middleware
from app.routers import users, pets

app = FastAPI(title="PetFeed API", version="1.0.0")

app.middleware("http")(telegram_auth_middleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(users.router, prefix="/v1")
app.include_router(pets.router, prefix="/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Запустить API и проверить вручную**

```bash
uvicorn app.main:app --reload
# Открыть http://localhost:8000/docs
```

- [ ] **Step 7: Запустить тесты**

```bash
pytest tests/test_pet_router.py -v
# Expected: PASS
```

- [ ] **Step 8: Commit**

```bash
git add app/main.py app/middleware/ app/routers/ tests/test_pet_router.py
git commit -m "feat: add FastAPI app with users and pets routers"
```

---

## Task 8: Telegram Bot — запуск и /start (SCR-01)

**Files:**
- Create: `bot/states.py`
- Create: `bot/keyboards.py`
- Create: `bot/handlers/start.py`
- Create: `bot/main.py`

- [ ] **Step 1: Создать `bot/states.py`**

```python
# bot/states.py
from aiogram.fsm.state import State, StatesGroup

class PetCreation(StatesGroup):
    waiting_species = State()
    waiting_breed   = State()
    waiting_name    = State()
    waiting_age     = State()
    waiting_weight  = State()
    waiting_confirm = State()
```

- [ ] **Step 2: Создать `bot/keyboards.py`**

```python
# bot/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def species_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🐱 Кошка",  callback_data="species:cat"),
            InlineKeyboardButton(text="🐶 Собака", callback_data="species:dog"),
        ],
        [
            InlineKeyboardButton(text="🐹 Грызун",  callback_data="species:rodent"),
            InlineKeyboardButton(text="🦜 Птица",   callback_data="species:bird"),
        ],
        [
            InlineKeyboardButton(text="🦎 Рептилия", callback_data="species:reptile"),
        ],
    ])

def breed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Метис / Не знаю", callback_data="breed:unknown")]
    ])

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm:save"),
            InlineKeyboardButton(text="✏️ Изменить",  callback_data="confirm:edit"),
        ]
    ])

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Рацион питания",       callback_data="menu:nutrition")],
        [InlineKeyboardButton(text="🚫 Что нельзя давать",    callback_data="menu:stoplist")],
        [InlineKeyboardButton(text="⏰ Напоминания",           callback_data="menu:reminders")],
        [InlineKeyboardButton(text="📊 Обновить вес",          callback_data="menu:weight")],
        [InlineKeyboardButton(text="🛒 Заказать корм",         callback_data="menu:order")],
        [InlineKeyboardButton(text="🤖 Задать вопрос AI",      callback_data="menu:ai")],
        [InlineKeyboardButton(text="🐾 Профиль питомца",       callback_data="menu:pet")],
    ])
```

- [ ] **Step 3: Создать `bot/handlers/start.py`**

```python
# bot/handlers/start.py
import httpx
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import species_keyboard, main_menu_keyboard
from app.config import settings

router = Router()

async def check_user_has_pet(telegram_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.BACKEND_URL}/v1/pets",
            headers={"X-Telegram-Id": str(telegram_id)}
        )
        if resp.status_code == 200:
            return len(resp.json()) > 0
    return False

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    has_pet = await check_user_has_pet(telegram_id)

    if has_pet:
        await message.answer(
            "👋 С возвращением! Выбери действие:",
            reply_markup=main_menu_keyboard()
        )
        return

    await message.answer(
        "🐾 Добро пожаловать в <b>PetFeed</b>!\n\n"
        "Я помогу правильно кормить твоего питомца — "
        "кошку, собаку, хомяка, черепаху или попугая.\n\n"
        "Давай создадим профиль питомца — это займёт 2 минуты.",
        parse_mode="HTML"
    )
    await state.set_state(PetCreation.waiting_species)
    await message.answer(
        "Шаг 1 из 5\nКто твой питомец?",
        reply_markup=species_keyboard()
    )
```

- [ ] **Step 4: Создать `bot/main.py`**

```python
# bot/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from app.config import settings
from bot.handlers import start

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.include_router(start.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Запустить бота и проверить /start**

```bash
python -m bot.main
# Открыть Telegram, найти бота, отправить /start
# Expected: приветственное сообщение + кнопки выбора вида животного
```

- [ ] **Step 6: Commit**

```bash
git add bot/ 
git commit -m "feat: add Telegram bot with /start handler and SCR-01"
```

---

## Task 9: FSM онбординг — SCR-02..SCR-07

**Files:**
- Create: `bot/handlers/pet_creation.py`
- Modify: `bot/main.py` — подключить новый роутер

- [ ] **Step 1: Создать `bot/handlers/pet_creation.py`**

```python
# bot/handlers/pet_creation.py
import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import PetCreation
from bot.keyboards import breed_keyboard, confirm_keyboard, main_menu_keyboard
from app.config import settings

router = Router()

SPECIES_LABELS = {
    "cat": "🐱 Кошка", "dog": "🐶 Собака", "rodent": "🐹 Грызун",
    "bird": "🦜 Птица", "reptile": "🦎 Рептилия"
}

# SCR-02: выбор вида
@router.callback_query(PetCreation.waiting_species, F.data.startswith("species:"))
async def process_species(callback: CallbackQuery, state: FSMContext):
    species = callback.data.split(":")[1]
    await state.update_data(species=species)
    await state.set_state(PetCreation.waiting_breed)
    await callback.message.edit_text(
        "Шаг 2 из 5\nКакая порода?\n\nНапиши породу или нажми кнопку:",
        reply_markup=breed_keyboard()
    )

# SCR-03: ввод породы текстом
@router.message(PetCreation.waiting_breed)
async def process_breed_text(message: Message, state: FSMContext):
    await state.update_data(breed=message.text.strip())
    await state.set_state(PetCreation.waiting_name)
    await message.answer("Шаг 3 из 5\nКак зовут питомца?")

# SCR-03: метис / не знаю
@router.callback_query(PetCreation.waiting_breed, F.data == "breed:unknown")
async def process_breed_unknown(callback: CallbackQuery, state: FSMContext):
    await state.update_data(breed=None)
    await state.set_state(PetCreation.waiting_name)
    await callback.message.edit_text("Шаг 3 из 5\nКак зовут питомца?")

# SCR-04: ввод имени
@router.message(PetCreation.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PetCreation.waiting_age)
    await message.answer(
        "Шаг 4 из 5\nСколько месяцев питомцу?\n\nВведи число месяцев. Например: 24 (= 2 года)"
    )

# SCR-05: ввод возраста
@router.message(PetCreation.waiting_age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.strip().isdigit() or int(message.text.strip()) < 0:
        await message.answer("❌ Введи число — количество месяцев. Например: 24")
        return
    await state.update_data(age_months=int(message.text.strip()))
    await state.set_state(PetCreation.waiting_weight)
    await message.answer("Шаг 5 из 5\nСколько весит питомец?\n\nВведи вес в кг. Например: 5.2")

# SCR-06: ввод веса
@router.message(PetCreation.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.strip().replace(",", "."))
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи вес в кг. Например: 5.2")
        return
    await state.update_data(weight_kg=weight)
    data = await state.get_data()
    breed_label = data.get("breed") or "Метис"
    summary = (
        f"Проверь данные питомца ✅\n\n"
        f"🐾 <b>{data['name']}</b>\n"
        f"Вид:     {SPECIES_LABELS.get(data['species'], data['species'])}\n"
        f"Порода:  {breed_label}\n"
        f"Возраст: {data['age_months']} мес\n"
        f"Вес:     {weight} кг"
    )
    await state.set_state(PetCreation.waiting_confirm)
    await message.answer(summary, parse_mode="HTML", reply_markup=confirm_keyboard())

# SCR-07: подтверждение — сохранить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:save")
async def confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = callback.from_user.id
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.BACKEND_URL}/v1/pets",
            json={
                "name": data["name"], "species": data["species"],
                "breed": data.get("breed"), "age_months": data["age_months"],
                "weight_kg": data["weight_kg"], "goal": "maintain"
            },
            headers={"X-Telegram-Id": str(telegram_id)}
        )
    await state.clear()
    if resp.status_code == 201:
        await callback.message.edit_text(
            f"✅ Профиль создан! Теперь я знаю как кормить <b>{data['name']}</b>.\n\n"
            "Выбери что хочешь сделать:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.message.edit_text("❌ Что-то пошло не так. Попробуй ещё раз /start")

# SCR-07: подтверждение — изменить
@router.callback_query(PetCreation.waiting_confirm, F.data == "confirm:edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PetCreation.waiting_species)
    from bot.keyboards import species_keyboard
    await callback.message.edit_text(
        "Шаг 1 из 5\nКто твой питомец?",
        reply_markup=species_keyboard()
    )
```

- [ ] **Step 2: Подключить роутер в `bot/main.py`**

```python
# bot/main.py — добавить импорт и регистрацию
from bot.handlers import start, pet_creation   # добавить pet_creation

# в функции main():
dp.include_router(start.router)
dp.include_router(pet_creation.router)         # добавить эту строку
```

- [ ] **Step 3: Запустить бота и пройти полный онбординг**

```bash
python -m bot.main
# Тест: /start → выбрать вид → ввести породу → ввести имя → возраст → вес → Сохранить
# Expected: профиль создан, показано главное меню
```

- [ ] **Step 4: Проверить питомца в БД**

```bash
docker exec -it $(docker-compose ps -q db) psql -U petfeed -d petfeed \
  -c "SELECT name, species, breed, age_months, weight_kg FROM pets;"
# Expected: строка с данными только что созданного питомца
```

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/pet_creation.py bot/main.py
git commit -m "feat: add FSM onboarding SCR-02..07 — full pet profile creation"
```

---

## Финальная проверка

- [ ] Запустить все тесты

```bash
pytest --cov=app tests/ -v
# Expected: все тесты PASS, coverage > 70% для services/
```

- [ ] Проверить полный флоу вручную: `/start` → онбординг → главное меню

- [ ] Commit финальный

```bash
git add .
git commit -m "feat: core system complete — FastAPI + PostgreSQL + Redis + Bot FSM onboarding"
```

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-core-system.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — свежий субагент на каждый Task, проверка между задачами, быстрые итерации

**2. Inline Execution** — выполнение в этой сессии через executing-plans, batch с чекпоинтами

**Какой подход выбираешь?**
