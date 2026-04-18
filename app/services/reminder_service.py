import re
from app.models.feeding_reminder import FeedingReminder
from app.repositories.reminder_repo import ReminderRepository

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class ReminderService:
    def __init__(self, repo: ReminderRepository):
        self.repo = repo

    def _validate_time(self, time_str: str) -> bool:
        return bool(TIME_RE.match(time_str.strip()))

    async def set_reminders(self, pet_id: int, user_id: int, times: list[str]) -> list[FeedingReminder]:
        for t in times:
            if not self._validate_time(t):
                raise ValueError(f"invalid_time: '{t}'. Format: HH:MM")
        await self.repo.delete_by_pet(pet_id)
        result = []
        for t in times:
            r = await self.repo.create(pet_id=pet_id, user_id=user_id, time_of_day=t.strip())
            result.append(r)
        return result

    async def get_by_pet(self, pet_id: int) -> list[FeedingReminder]:
        return await self.repo.get_by_pet(pet_id)

    async def get_all_active(self) -> list[FeedingReminder]:
        return await self.repo.get_all_active()
