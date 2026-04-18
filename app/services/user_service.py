from app.models.user import User
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> User:
        user = await self.repo.get_by_telegram_id(telegram_id)
        if user is None:
            user = await self.repo.create(telegram_id=telegram_id, username=username)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.repo.get_by_telegram_id(telegram_id)
