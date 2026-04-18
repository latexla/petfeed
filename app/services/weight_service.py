from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pet import Pet
from app.models.weight_history import WeightHistory
from app.repositories.pet_repo import PetRepository
from app.repositories.nutrition_repo import NutritionRepository
from app.services.nutrition_service import NutritionService

RECALC_THRESHOLD = 0.05  # пересчитываем рацион при изменении веса >= 5%


class WeightService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_weight(self, pet: Pet, new_weight_kg: float) -> tuple[Pet, bool]:
        """Returns (updated_pet, ration_recalculated)"""
        old_weight = float(pet.weight_kg)
        change_ratio = abs(new_weight_kg - old_weight) / old_weight

        history = WeightHistory(pet_id=pet.id, weight_kg=new_weight_kg)
        self.session.add(history)

        repo = PetRepository(self.session)
        updated_pet = await repo.update(pet, weight_kg=new_weight_kg)

        recalculated = False
        if change_ratio >= RECALC_THRESHOLD:
            nutrition_service = NutritionService(NutritionRepository(self.session))
            await nutrition_service.calculate_and_save(updated_pet)
            recalculated = True

        return updated_pet, recalculated

    async def get_history(self, pet_id: int, limit: int = 10) -> list[WeightHistory]:
        result = await self.session.execute(
            select(WeightHistory)
            .where(WeightHistory.pet_id == pet_id)
            .order_by(WeightHistory.recorded_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
