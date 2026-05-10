from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.redis_client import get_redis
from app.repositories.user_repo import UserRepository
from app.services.auth_service import (
    create_jwt,
    create_refresh_token,
    delete_refresh_token,
    verify_initdata,
    verify_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE = dict(httponly=True, secure=True, samesite="none", max_age=604800)


class InitDataRequest(BaseModel):
    init_data: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


@router.post("/miniapp", response_model=TokenResponse)
async def auth_miniapp(
    body: InitDataRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        user_data = verify_initdata(body.init_data, settings.TELEGRAM_BOT_TOKEN)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="missing user id in initData")

    repo = UserRepository(db)
    user = await repo.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=403,
            detail="user not registered — start the bot first: @PetFeedBot",
        )

    access_token = create_jwt(telegram_id, settings.JWT_SECRET, settings.JWT_ALGORITHM)
    refresh = await create_refresh_token(telegram_id, redis)
    response.set_cookie(key="refresh_token", value=refresh, **_COOKIE)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis=Depends(get_redis),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="no refresh token")
    try:
        telegram_id = await verify_refresh_token(refresh_token, redis)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid refresh token")

    await delete_refresh_token(refresh_token, redis)
    new_refresh = await create_refresh_token(telegram_id, redis)

    access_token = create_jwt(telegram_id, settings.JWT_SECRET, settings.JWT_ALGORITHM)

    response.set_cookie(key="refresh_token", value=new_refresh, **_COOKIE)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis=Depends(get_redis),
):
    if refresh_token:
        await delete_refresh_token(refresh_token, redis)
    response.delete_cookie("refresh_token")
    return {"status": "ok"}
