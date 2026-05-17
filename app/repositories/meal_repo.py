import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.food_item import FoodItem
from app.models.stop_food import StopFood
from app.redis_client import get_redis

MEAL_SESSION_TTL = 1800   # 30 min
DEEPSEEK_CACHE_TTL = 86400  # 24h
DAILY_TRACKER_TTL = 86400  # 24h — full day session


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

    # ── Daily tracker session ───────────────────────────────────────

    def _daily_key(self, telegram_id: int, pet_id: int) -> str:
        return f"daily:{telegram_id}:{pet_id}"

    async def get_daily_session(self, telegram_id: int, pet_id: int) -> dict | None:
        redis = get_redis()
        raw = await redis.get(self._daily_key(telegram_id, pet_id))
        return json.loads(raw) if raw else None

    async def save_daily_session(self, telegram_id: int, pet_id: int, data: dict) -> None:
        redis = get_redis()
        await redis.set(
            self._daily_key(telegram_id, pet_id),
            json.dumps(data, ensure_ascii=False),
            ex=DAILY_TRACKER_TTL,
        )

    async def delete_daily_session(self, telegram_id: int, pet_id: int) -> None:
        redis = get_redis()
        await redis.delete(self._daily_key(telegram_id, pet_id))

    # ── Food search ─────────────────────────────────────────────────

    async def search_food_items(self, q: str, species: str, limit: int = 10) -> list[FoodItem]:
        from sqlalchemy import or_, func
        result = await self.session.execute(
            select(FoodItem)
            .where(
                FoodItem.species.in_([species, "all"]),
                or_(
                    func.lower(FoodItem.name).contains(q.lower()),
                    func.lower(FoodItem.name_aliases).contains(q.lower()),
                ),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_food_item_by_id(self, food_item_id: int) -> FoodItem | None:
        result = await self.session.execute(
            select(FoodItem).where(FoodItem.id == food_item_id)
        )
        return result.scalar_one_or_none()

    # ── Feeding session persistence ─────────────────────────────────

    async def save_feeding_session(
        self,
        pet_id: int,
        session_date,
        total_kcal: float,
        protein_g: float,
        fat_g: float,
        items_count: int,
        score: int,
        quality: str,
        tips: list[str],
        kcal_pct: float | None = None,
    ) -> None:
        from app.models.feeding_session import FeedingSession
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(FeedingSession).values(
            pet_id=pet_id,
            session_date=session_date,
            total_kcal=round(total_kcal, 2),
            protein_g=round(protein_g, 2),
            fat_g=round(fat_g, 2),
            kcal_pct=round(kcal_pct, 1) if kcal_pct is not None else None,
            items_count=items_count,
            score=score,
            quality=quality,
            tips=json.dumps(tips, ensure_ascii=False),
        ).on_conflict_do_update(
            constraint="uq_feeding_sessions_pet_date",
            set_={
                "total_kcal": round(total_kcal, 2),
                "protein_g": round(protein_g, 2),
                "fat_g": round(fat_g, 2),
                "kcal_pct": round(kcal_pct, 1) if kcal_pct is not None else None,
                "items_count": items_count,
                "score": score,
                "quality": quality,
                "tips": json.dumps(tips, ensure_ascii=False),
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_feeding_history(self, pet_id: int, limit: int = 30) -> list:
        from app.models.feeding_session import FeedingSession
        from sqlalchemy import desc
        result = await self.session.execute(
            select(FeedingSession)
            .where(FeedingSession.pet_id == pet_id)
            .order_by(desc(FeedingSession.session_date))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def scan_daily_keys(self) -> list[str]:
        """Return all daily:*:* Redis keys — used by scheduler."""
        redis = get_redis()
        keys: list[str] = []
        cursor = 0
        while True:
            cursor, batch = await redis.scan(cursor, match="daily:*:*", count=100)
            keys.extend(batch)
            if cursor == 0:
                break
        return keys

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
