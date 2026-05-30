import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.auth import telegram_auth_middleware
from app.observability import setup_observability
from app.routers import admin, ai, auth, breeds, feedback, meal, nutrition, pets, reminders, users, weight

setup_observability("api")
_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.models  # noqa: F401
    yield


app = FastAPI(title="PetFeed API", version="1.0.0", lifespan=lifespan)

app.middleware("http")(telegram_auth_middleware)

_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if not _origins:
    if settings.APP_ENV == "production":
        raise RuntimeError("ALLOWED_ORIGINS must be set in production")
    _log.warning("ALLOWED_ORIGINS is empty — falling back to '*' (development only)")
    _origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
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
app.include_router(auth.router, prefix="/v1")
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
