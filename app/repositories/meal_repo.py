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
