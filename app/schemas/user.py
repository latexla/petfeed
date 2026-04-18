from datetime import datetime
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    is_active: bool
    ai_requests_today: int
    created_at: datetime

    model_config = {"from_attributes": True}
