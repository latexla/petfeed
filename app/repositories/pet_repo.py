from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pet import Pet


class PetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Pet:
        pet = Pet(**kwargs)
        self.session.add(pet)
        await self.session.commit()
        await self.session.refresh(pet)
        return pet

    async def get_by_owner(self, owner_id: int) -> list[Pet]:
        result = await self.session.execute(
            select(Pet).where(Pet.owner_id == owner_id, Pet.is_active == True)
        )
        return list(result.scalars().all())

    async def get_by_id(self, pet_id: int, owner_id: int) -> Pet | None:
        result = await self.session.execute(
            select(Pet).where(Pet.id == pet_id, Pet.owner_id == owner_id, Pet.is_active == True)
        )
        return result.scalar_one_or_none()

    async def update(self, pet: Pet, **kwargs) -> Pet:
        for key, value in kwargs.items():
            setattr(pet, key, value)
        await self.session.commit()
        await self.session.refresh(pet)
        return pet
