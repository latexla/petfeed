from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware.auth import telegram_auth_middleware
from app.routers import users, pets, nutrition, reminders, ai, weight, breeds, meal, feedback
from app.routers import admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, Base
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="PetFeed API", version="1.0.0", lifespan=lifespan)

app.middleware("http")(telegram_auth_middleware)
_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Telegram-Id", "X-Api-Key", "X-Admin-Token"],
)

app.include_router(users.router, prefix="/v1")
app.include_router(pets.router, prefix="/v1")
app.include_router(nutrition.router, prefix="/v1")
app.include_router(reminders.router, prefix="/v1")
app.include_router(ai.router, prefix="/v1")
app.include_router(weight.router, prefix="/v1")
app.include_router(breeds.router, prefix="/v1")
app.include_router(meal.router, prefix="/v1")
app.include_router(feedback.router, prefix="/v1")
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
