from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import telegram_auth_middleware
from app.routers import users, pets, nutrition, reminders, ai, weight


@asynccontextmanager
async def lifespan(app: FastAPI):
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
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
