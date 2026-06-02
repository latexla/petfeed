from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.feature_flag_service import is_enabled


def _db_returning(flag):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = flag
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_cache_hit_skips_db():
    redis = AsyncMock()
    redis.get.return_value = "1"
    db = AsyncMock()
    with patch("app.services.feature_flag_service.get_redis", return_value=redis):
        assert await is_enabled("feature_food_catalog", db) is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_missing_flag_defaults_true():
    redis = AsyncMock()
    redis.get.return_value = None
    db = _db_returning(None)
    with patch("app.services.feature_flag_service.get_redis", return_value=redis):
        assert await is_enabled("feature_food_catalog", db) is True


@pytest.mark.asyncio
async def test_disabled_flag_from_db():
    redis = AsyncMock()
    redis.get.return_value = None
    flag = MagicMock(); flag.is_enabled = False
    db = _db_returning(flag)
    with patch("app.services.feature_flag_service.get_redis", return_value=redis):
        assert await is_enabled("feature_food_catalog", db) is False
    redis.set.assert_awaited()  # result cached
