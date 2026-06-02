from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag
from app.redis_client import get_redis

FLAG_CACHE_TTL = 60  # seconds, per CLAUDE.md


def _cache_key(key: str) -> str:
    return f"flag:{key}"


async def is_enabled(key: str, db: AsyncSession, default: bool = True) -> bool:
    """Return flag state. Cached in Redis (TTL 60s). Missing flag -> default."""
    redis = get_redis()
    cached = await redis.get(_cache_key(key))
    if cached is not None:
        return cached == "1"

    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalar_one_or_none()
    enabled = flag.is_enabled if flag is not None else default

    await redis.set(_cache_key(key), "1" if enabled else "0", ex=FLAG_CACHE_TTL)
    return enabled
