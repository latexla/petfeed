from app.models.pet import Pet
from app.repositories.pet_repo import PetRepository

ALLOWED_SPECIES = {"cat", "dog", "rodent", "bird", "reptile"}
ALLOWED_GOALS = {"maintain", "lose", "gain", "growth"}


class PetService:
    def __init__(self, repo: PetRepository):
        self.repo = repo

    async def create(self, owner_id: int, name: str, species: str,
                     age_months: int, weight_kg: float, goal: str = "maintain",
                     breed: str | None = None, is_neutered: bool = False,
                     activity_level: str = "moderate", physio_status: str = "normal",
                     food_category_id: int | None = None) -> Pet:
        if species not in ALLOWED_SPECIES:
            raise ValueError(f"invalid_species: {species}. Allowed: {ALLOWED_SPECIES}")
        if goal not in ALLOWED_GOALS:
            raise ValueError(f"invalid_goal: {goal}. Allowed: {ALLOWED_GOALS}")
        if age_months < 0:
            raise ValueError("invalid_age: age_months must be >= 0")
        if weight_kg <= 0:
            raise ValueError("invalid_weight: weight_kg must be > 0")
        if goal == "growth" and age_months >= 18:
            raise ValueError("invalid_goal: growth is only for animals under 18 months")
        return await self.repo.create(
            owner_id=owner_id, name=name, species=species, breed=breed,
            age_months=age_months, weight_kg=weight_kg, goal=goal,
            is_neutered=is_neutered, activity_level=activity_level,
            physio_status=physio_status, food_category_id=food_category_id,
        )

    async def get_by_owner(self, owner_id: int) -> list[Pet]:
        return await self.repo.get_by_owner(owner_id)

    async def get_by_id(self, pet_id: int, owner_id: int) -> Pet | None:
        return await self.repo.get_by_id(pet_id=pet_id, owner_id=owner_id)

    async def update(self, pet_id: int, owner_id: int, **kwargs) -> Pet | None:
        pet = await self.repo.get_by_id(pet_id=pet_id, owner_id=owner_id)
        if pet is None:
            return None
        if "species" in kwargs and kwargs["species"] not in ALLOWED_SPECIES:
            raise ValueError("invalid_species")
        return await self.repo.update(pet, **kwargs)

    async def delete(self, pet_id: int, owner_id: int) -> bool:
        pet = await self.repo.get_by_id(pet_id=pet_id, owner_id=owner_id)
        if pet is None:
            return False
        await self.repo.delete(pet)
        return True
