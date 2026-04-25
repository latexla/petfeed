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


class StopFoodItem(BaseModel):
    product_name: str
    toxic_component: str | None
    clinical_effect: str | None


class RationResponse(BaseModel):
    pet_id: int
    daily_calories: float
    daily_food_grams: float
    meals_per_day: int
    food_per_meal_grams: float
    protein_min_g: float
    fat_min_g: float
    stop_foods_level1: list[StopFoodItem]
    stop_foods_level2: list[StopFoodItem]
    stop_foods_level3: list[StopFoodItem]
    recommendations: list[str]
    hypoglycemia_warning: bool
    notes: str
    stop_foods: str


@router.get("/food-categories", response_model=list[dict])
async def get_food_categories(db: AsyncSession = Depends(get_db)):
    repo = NutritionRepository(db)
    cats = await repo.get_all_food_categories()
    return [
        {
            "id": c.id,
            "name": c.name,
            "food_type": c.food_type,
            "kcal_per_100g": float(c.kcal_per_100g),
        }
        for c in cats
    ]


@router.get("/{pet_id}", response_model=RationResponse)
async def get_ration(pet_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(
        telegram_id=request.state.telegram_id
    )
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    service = NutritionService(NutritionRepository(db))
    result = await service.calculate_and_save(pet)

    stop_foods_str = ", ".join(
        f["product_name"] for f in result.stop_foods_level1
    )

    return RationResponse(
        pet_id=pet.id,
        daily_calories=result.daily_calories,
        daily_food_grams=result.daily_food_grams,
        meals_per_day=result.meals_per_day,
        food_per_meal_grams=result.food_per_meal_grams,
        protein_min_g=result.protein_min_g,
        fat_min_g=result.fat_min_g,
        stop_foods_level1=[StopFoodItem(**s) for s in result.stop_foods_level1],
        stop_foods_level2=[StopFoodItem(**s) for s in result.stop_foods_level2],
        stop_foods_level3=[StopFoodItem(**s) for s in result.stop_foods_level3],
        recommendations=result.recommendations,
        hypoglycemia_warning=result.hypoglycemia_warning,
        notes=result.notes,
        stop_foods=stop_foods_str,
    )
