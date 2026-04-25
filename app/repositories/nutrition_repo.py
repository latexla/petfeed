from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.nutrition_knowledge import NutritionKnowledge
from app.models.ration import Ration
from app.models.food_category import FoodCategory
from app.models.breed_risk import BreedRisk
from app.models.stop_food import StopFood


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

    async def get_food_category(self, category_id: int) -> FoodCategory | None:
        return await self.session.get(FoodCategory, category_id)

    async def get_all_food_categories(self) -> list[FoodCategory]:
        result = await self.session.execute(select(FoodCategory).order_by(FoodCategory.id))
        return list(result.scalars().all())

    async def get_breed_risks(self, breed_name: str) -> list[str]:
        if not breed_name:
            return []
        result = await self.session.execute(
            select(BreedRisk.risk_key).where(BreedRisk.breed_name == breed_name)
        )
        return list(result.scalars().all())

    async def get_stop_foods(self, species: str, level: int) -> list[dict]:
        result = await self.session.execute(
            select(StopFood).where(
                StopFood.level == level,
                StopFood.species.in_([species, "all"])
            )
        )
        foods = result.scalars().all()
        return [
            {
                "product_name": f.product_name,
                "toxic_component": f.toxic_component,
                "clinical_effect": f.clinical_effect,
            }
            for f in foods
        ]

    async def get_ration_by_pet(self, pet_id: int) -> Ration | None:
        result = await self.session.execute(
            select(Ration).where(Ration.pet_id == pet_id)
        )
        return result.scalar_one_or_none()

    async def upsert_ration(self, pet_id: int, daily_calories: float,
                            daily_food_grams: float, meals_per_day: int,
                            food_per_meal_grams: float, notes: str | None) -> Ration:
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
            pet_id=pet_id, daily_calories=daily_calories,
            daily_food_grams=daily_food_grams, meals_per_day=meals_per_day,
            food_per_meal_grams=food_per_meal_grams, notes=notes
        )
        self.session.add(ration)
        await self.session.commit()
        await self.session.refresh(ration)
        return ration
