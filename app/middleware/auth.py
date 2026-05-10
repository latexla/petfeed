from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.auth_service import verify_jwt

PUBLIC_PATHS = [
    "/docs", "/openapi.json", "/health",
    "/v1/orders/webhook", "/admin", "/v1/auth",
]


async def telegram_auth_middleware(request: Request, call_next):
    if any(request.url.path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            telegram_id = verify_jwt(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
            request.state.telegram_id = telegram_id
            return await call_next(request)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "invalid or expired token"},
            )

    telegram_id = request.headers.get("X-Telegram-Id")
    if not telegram_id or not telegram_id.isdigit():
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "X-Telegram-Id header required"},
        )
    request.state.telegram_id = int(telegram_id)
    return await call_next(request)
