from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.nutrition_knowledge import NutritionKnowledge
from app.models.ration import Ration


class NutritionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_knowledge(self, species: str, goal: str) -> NutritionKnowledge | None:
        result = await self.session.execute(
            select(NutritionKnowledge).where(
                NutritionKnowledge.species == species,
                NutritionKnowledge.goal == goal
            )
        )
        return result.scalar_one_or_none()

    async def get_ration_by_pet(self, pet_id: int) -> Ration | None:
        result = await self.session.execute(
            select(Ration).where(Ration.pet_id == pet_id)
        )
        return result.scalar_one_or_none()

    async def upsert_ration(self, pet_id: int, daily_calories: float, daily_food_grams: float,
                            meals_per_day: int, food_per_meal_grams: float, notes: str | None) -> Ration:
        existing = await self.get_ration_by_pet(pet_id)
        if existing:
            existing.daily_calories = daily_calories
            existing.daily_food_grams = daily_food_grams
            existing.meals_per_day = meals_per_day
            existing.food_per_meal_grams = food_per_meal_grams
            existing.notes = notes
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        ration = Ration(
            pet_id=pet_id, daily_calories=daily_calories, daily_food_grams=daily_food_grams,
            meals_per_day=meals_per_day, food_per_meal_grams=food_per_meal_grams, notes=notes
        )
        self.session.add(ration)
        await self.session.commit()
        await self.session.refresh(ration)
        return ration
