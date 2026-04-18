from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    telegram_id = request.state.telegram_id
    service = UserService(UserRepository(db))
    user = await service.get_or_create(telegram_id=telegram_id)
    return user
