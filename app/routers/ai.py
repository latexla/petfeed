from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.ai_service import AiService

router = APIRouter(prefix="/ai", tags=["ai"])


class AskRequest(BaseModel):
    question: str
    pet_id: int | None = None


class AskResponse(BaseModel):
    answer: str
    cache_hit: bool
    requests_left: int


@router.post("/ask", response_model=AskResponse)
async def ask_ai(data: AskRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=request.state.telegram_id)
    ai_service = AiService(db)

    can_ask, remaining = await ai_service.check_limit(user)
    if not can_ask:
        raise HTTPException(status_code=429, detail={
            "error": "daily_limit_exceeded",
            "message": f"Лимит {10} запросов/день исчерпан"
        })

    pet = None
    if data.pet_id:
        pet = await PetService(PetRepository(db)).get_by_id(pet_id=data.pet_id, owner_id=user.id)

    answer, cache_hit = await ai_service.ask(user=user, pet=pet, question=data.question)
    _, remaining = await ai_service.check_limit(user)
    return AskResponse(answer=answer, cache_hit=cache_hit, requests_left=remaining)
