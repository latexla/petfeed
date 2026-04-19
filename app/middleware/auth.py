from fastapi import Request
from fastapi.responses import JSONResponse

PUBLIC_PATHS = ["/docs", "/openapi.json", "/health", "/v1/orders/webhook", "/admin"]


async def telegram_auth_middleware(request: Request, call_next):
    if any(request.url.path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    telegram_id = request.headers.get("X-Telegram-Id")
    if not telegram_id or not telegram_id.isdigit():
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "X-Telegram-Id header required"}
        )
    request.state.telegram_id = int(telegram_id)
    return await call_next(request)
