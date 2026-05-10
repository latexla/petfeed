import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

import jwt
from redis.asyncio import Redis


def verify_initdata(init_data: str, bot_token: str) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("invalid hash")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 3600:
        raise ValueError("initData expired")

    return json.loads(parsed.get("user", "{}"))


def create_jwt(telegram_id: int, secret: str, algorithm: str = "HS256") -> str:
    payload = {
        "sub": str(telegram_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def verify_jwt(token: str, secret: str, algorithm: str = "HS256") -> int:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return int(payload["sub"])
    except jwt.PyJWTError as exc:
        raise ValueError(f"invalid token: {exc}") from exc


async def create_refresh_token(telegram_id: int, redis: Redis) -> str:
    token = str(uuid.uuid4())
    await redis.setex(f"refresh:{token}", 604800, str(telegram_id))
    return token


async def verify_refresh_token(token: str, redis: Redis) -> int:
    value = await redis.get(f"refresh:{token}")
    if not value:
        raise ValueError("invalid or expired refresh token")
    return int(value)


async def delete_refresh_token(token: str, redis: Redis) -> None:
    await redis.delete(f"refresh:{token}")
