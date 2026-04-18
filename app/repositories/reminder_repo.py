from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.feeding_reminder import FeedingReminder


class ReminderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_pet(self, pet_id: int) -> list[FeedingReminder]:
        result = await self.session.execute(
            select(FeedingReminder).where(
                FeedingReminder.pet_id == pet_id,
                FeedingReminder.is_active == True
            ).order_by(FeedingReminder.time_of_day)
        )
        return list(result.scalars().all())

    async def get_all_active(self) -> list[FeedingReminder]:
        result = await self.session.execute(
            select(FeedingReminder).where(FeedingReminder.is_active == True)
        )
        return list(result.scalars().all())

    async def create(self, pet_id: int, user_id: int, time_of_day: str) -> FeedingReminder:
        reminder = FeedingReminder(pet_id=pet_id, user_id=user_id, time_of_day=time_of_day)
        self.session.add(reminder)
        await self.session.commit()
        await self.session.refresh(reminder)
        return reminder

    async def delete_by_pet(self, pet_id: int) -> None:
        await self.session.execute(
            delete(FeedingReminder).where(FeedingReminder.pet_id == pet_id)
        )
        await self.session.commit()
