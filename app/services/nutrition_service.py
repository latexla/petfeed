from dataclasses import dataclass
from app.models.pet import Pet
from app.models.ration import Ration
from app.repositories.nutrition_repo import NutritionRepository


@dataclass
class RationResult:
    daily_calories: float
    daily_food_grams: float
    meals_per_day: int
    food_per_meal_grams: float
    stop_foods: str
    notes: str
    ration: Ration


class NutritionService:
    def __init__(self, repo: NutritionRepository):
        self.repo = repo

    def _rer(self, weight_kg: float) -> float:
        """Resting Energy Requirement: 70 × weight^0.75"""
        return 70 * (weight_kg ** 0.75)

    async def calculate_and_save(self, pet: Pet) -> RationResult:
        weight = float(pet.weight_kg)
        knowledge = await self.repo.get_knowledge(pet.species, pet.goal)

        if knowledge is None:
            # fallback to maintain if goal not found
            knowledge = await self.repo.get_knowledge(pet.species, "maintain")

        rer = self._rer(weight)
        daily_calories = round(rer * float(knowledge.rer_multiplier), 1)
        kcal_per_100g = float(knowledge.kcal_per_100g)
        daily_food_grams = round((daily_calories / kcal_per_100g) * 100, 1)
        meals = knowledge.meals_per_day
        food_per_meal = round(daily_food_grams / meals, 1)

        ration = await self.repo.upsert_ration(
            pet_id=pet.id,
            daily_calories=daily_calories,
            daily_food_grams=daily_food_grams,
            meals_per_day=meals,
            food_per_meal_grams=food_per_meal,
            notes=knowledge.notes
        )

        return RationResult(
            daily_calories=daily_calories,
            daily_food_grams=daily_food_grams,
            meals_per_day=meals,
            food_per_meal_grams=food_per_meal,
            stop_foods=knowledge.stop_foods or "",
            notes=knowledge.notes or "",
            ration=ration
        )

    async def get_ration(self, pet_id: int) -> Ration | None:
        return await self.repo.get_ration_by_pet(pet_id)
