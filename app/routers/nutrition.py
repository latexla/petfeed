from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.nutrition_repo import NutritionRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


class RationResponse(BaseModel):
    pet_id: int
    daily_calories: float
    daily_food_grams: float
    meals_per_day: int
    food_per_meal_grams: float
    stop_foods: str
    notes: str


@router.get("/{pet_id}", response_model=RationResponse)
async def get_ration(pet_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=request.state.telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    service = NutritionService(NutritionRepository(db))
    result = await service.calculate_and_save(pet)
    return RationResponse(
        pet_id=pet.id,
        daily_calories=result.daily_calories,
        daily_food_grams=result.daily_food_grams,
        meals_per_day=result.meals_per_day,
        food_per_meal_grams=result.food_per_meal_grams,
        stop_foods=result.stop_foods,
        notes=result.notes
    )
