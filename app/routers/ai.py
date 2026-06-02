from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.pet_repo import PetRepository
from app.repositories.user_repo import UserRepository
from app.services.ai_service import AiService
from app.services.pet_service import PetService
from app.services.user_service import UserService

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

    foods = []
    if pet is not None:
        from app.services.feature_flag_service import is_enabled
        if await is_enabled("feature_food_catalog", db):
            from app.repositories.commercial_food_repo import CommercialFoodRepository
            from app.repositories.nutrition_repo import NutritionRepository
            from app.services.commercial_food_service import CommercialFoodService
            cf_repo = CommercialFoodRepository(db)
            cf_svc = CommercialFoodService(cf_repo)
            risks = await NutritionRepository(db).get_breed_risks(pet.breed or "")
            filt = cf_svc.pet_to_filters(pet, risks)
            foods = cf_svc.rank(
                await cf_repo.filter(species=filt["species"],
                                     life_stage=filt["life_stage"], limit=10),
                filt,
            )[:5]

    answer, cache_hit = await ai_service.ask(
        user=user, pet=pet, question=data.question, foods=foods,
    )
    _, remaining = await ai_service.check_limit(user)
    return AskResponse(answer=answer, cache_hit=cache_hit, requests_left=remaining)
