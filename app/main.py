from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import telegram_auth_middleware
from app.routers import users, pets, nutrition, reminders, ai, weight


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, Base
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="PetFeed API", version="1.0.0", lifespan=lifespan)

app.middleware("http")(telegram_auth_middleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(users.router, prefix="/v1")
app.include_router(pets.router, prefix="/v1")
app.include_router(nutrition.router, prefix="/v1")
app.include_router(reminders.router, prefix="/v1")
app.include_router(ai.router, prefix="/v1")
app.include_router(weight.router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/admin/seed")
async def seed_nutrition(db: AsyncSession = Depends(get_db)):
    from app.models.nutrition_knowledge import NutritionKnowledge
    from sqlalchemy import select
    existing = await db.execute(select(NutritionKnowledge))
    if existing.scalars().first():
        return {"status": "already seeded"}
    records = [
        NutritionKnowledge(species="cat", goal="maintain", rer_multiplier=1.2, meals_per_day=2, kcal_per_100g=350.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Облигатный хищник"),
        NutritionKnowledge(species="cat", goal="lose", rer_multiplier=0.8, meals_per_day=3, kcal_per_100g=300.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Снижение веса"),
        NutritionKnowledge(species="cat", goal="gain", rer_multiplier=1.4, meals_per_day=3, kcal_per_100g=400.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Набор веса"),
        NutritionKnowledge(species="cat", goal="growth", rer_multiplier=1.6, meals_per_day=4, kcal_per_100g=380.0, stop_foods="лук, чеснок, виноград, шоколад", notes="Котёнок до 1 года"),
        NutritionKnowledge(species="dog", goal="maintain", rer_multiplier=1.3, meals_per_day=2, kcal_per_100g=320.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Взрослая собака"),
        NutritionKnowledge(species="dog", goal="lose", rer_multiplier=1.0, meals_per_day=3, kcal_per_100g=280.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Снижение веса"),
        NutritionKnowledge(species="dog", goal="gain", rer_multiplier=1.6, meals_per_day=3, kcal_per_100g=380.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Набор веса"),
        NutritionKnowledge(species="dog", goal="growth", rer_multiplier=2.0, meals_per_day=4, kcal_per_100g=360.0, stop_foods="лук, виноград, изюм, шоколад, ксилит", notes="Щенок до 1 года"),
        NutritionKnowledge(species="rodent", goal="maintain", rer_multiplier=1.1, meals_per_day=2, kcal_per_100g=250.0, stop_foods="цитрусовые, сахар, соль", notes="Хомяк/крыса/морская свинка"),
        NutritionKnowledge(species="rodent", goal="growth", rer_multiplier=1.4, meals_per_day=3, kcal_per_100g=280.0, stop_foods="цитрусовые, сахар, соль", notes="Молодой грызун"),
        NutritionKnowledge(species="bird", goal="maintain", rer_multiplier=1.0, meals_per_day=2, kcal_per_100g=200.0, stop_foods="авокадо, шоколад, кофеин, соль", notes="Попугай/канарейка"),
        NutritionKnowledge(species="bird", goal="growth", rer_multiplier=1.3, meals_per_day=3, kcal_per_100g=220.0, stop_foods="авокадо, шоколад, кофеин, соль", notes="Птенец"),
        NutritionKnowledge(species="reptile", goal="maintain", rer_multiplier=0.6, meals_per_day=1, kcal_per_100g=180.0, stop_foods="обработанные продукты", notes="Черепаха/ящерица"),
        NutritionKnowledge(species="reptile", goal="growth", rer_multiplier=0.9, meals_per_day=2, kcal_per_100g=200.0, stop_foods="обработанные продукты", notes="Молодая рептилия"),
    ]
    db.add_all(records)
    await db.commit()
    return {"status": "seeded", "count": len(records)}
