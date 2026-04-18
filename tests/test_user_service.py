import pytest
from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository


@pytest.mark.asyncio
async def test_get_or_create_user_creates_new(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    user = await service.get_or_create(telegram_id=123456, username="testuser")
    assert user.id is not None
    assert user.telegram_id == 123456
    assert user.username == "testuser"
    assert user.ai_requests_today == 0


@pytest.mark.asyncio
async def test_get_or_create_user_returns_existing(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    user1 = await service.get_or_create(telegram_id=111, username="user1")
    user2 = await service.get_or_create(telegram_id=111, username="user1")
    assert user1.id == user2.id


@pytest.mark.asyncio
async def test_get_by_telegram_id(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    await service.get_or_create(telegram_id=999, username="findme")
    user = await service.get_by_telegram_id(999)
    assert user is not None
    assert user.username == "findme"
