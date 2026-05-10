import hashlib
import hmac
import json
import time
import urllib.parse

import pytest

from app.services.auth_service import create_jwt, verify_initdata, verify_jwt


BOT_TOKEN = "1234567890:AAtest_token_for_testing_only"


def _make_initdata(telegram_id: int = 123, age_offset: int = 0) -> str:
    user = json.dumps({"id": telegram_id, "first_name": "Test", "username": "tester"})
    auth_date = str(int(time.time()) - age_offset)
    fields = {"user": user, "auth_date": auth_date, "query_id": "test_query"}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    hash_ = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    fields["hash"] = hash_
    return urllib.parse.urlencode(fields)


def test_verify_initdata_valid():
    result = verify_initdata(_make_initdata(telegram_id=456), BOT_TOKEN)
    assert result["id"] == 456


def test_verify_initdata_wrong_token():
    with pytest.raises(ValueError, match="invalid hash"):
        verify_initdata(_make_initdata(), "wrong:token")


def test_verify_initdata_expired():
    with pytest.raises(ValueError, match="expired"):
        verify_initdata(_make_initdata(age_offset=3601), BOT_TOKEN)


def test_verify_initdata_missing_hash():
    with pytest.raises(ValueError, match="missing hash"):
        verify_initdata("auth_date=123&user=%7B%7D", BOT_TOKEN)


def test_jwt_roundtrip():
    token = create_jwt(telegram_id=789, secret="test-secret")
    assert verify_jwt(token, "test-secret") == 789


def test_jwt_wrong_secret():
    token = create_jwt(telegram_id=1, secret="correct")
    with pytest.raises(ValueError):
        verify_jwt(token, "wrong")


def test_jwt_bad_token():
    with pytest.raises(ValueError):
        verify_jwt("not.a.valid.token", "any")


from unittest.mock import AsyncMock, MagicMock

from app.services.auth_service import (
    create_refresh_token, verify_refresh_token, delete_refresh_token
)


@pytest.mark.asyncio
async def test_create_refresh_token_stores_in_redis():
    redis = MagicMock()
    redis.setex = AsyncMock()
    token = await create_refresh_token(telegram_id=42, redis=redis)
    assert len(token) == 36  # UUID4 format
    redis.setex.assert_called_once()
    call_args = redis.setex.call_args
    assert call_args[0][0] == f"refresh:{token}"
    assert call_args[0][1] == 604800
    assert call_args[0][2] == "42"


@pytest.mark.asyncio
async def test_verify_refresh_token_returns_telegram_id():
    redis = MagicMock()
    redis.get = AsyncMock(return_value="99")
    result = await verify_refresh_token("some-uuid", redis)
    assert result == 99
    redis.get.assert_called_once_with("refresh:some-uuid")


@pytest.mark.asyncio
async def test_verify_refresh_token_raises_on_missing():
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="invalid or expired"):
        await verify_refresh_token("bad-token", redis)


@pytest.mark.asyncio
async def test_delete_refresh_token_deletes_key():
    redis = MagicMock()
    redis.delete = AsyncMock()
    await delete_refresh_token("some-uuid", redis)
    redis.delete.assert_called_once_with("refresh:some-uuid")
