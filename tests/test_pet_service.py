import pytest
from app.services.pet_service import PetService
from app.services.user_service import UserService
from app.repositories.pet_repo import PetRepository
from app.repositories.user_repo import UserRepository


@pytest.mark.asyncio
async def test_create_pet(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=1, username="u")
    service = PetService(PetRepository(db_session))
    pet = await service.create(
        owner_id=user.id, name="Барсик", species="cat",
        breed="Мейн-кун", age_months=24, weight_kg=5.2, goal="maintain"
    )
    assert pet.id is not None
    assert pet.name == "Барсик"
    assert pet.species == "cat"


@pytest.mark.asyncio
async def test_get_pet_by_owner(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=2, username="u2")
    service = PetService(PetRepository(db_session))
    await service.create(owner_id=user.id, name="Рекс", species="dog",
                         age_months=36, weight_kg=28.5, goal="lose")
    pets = await service.get_by_owner(user.id)
    assert len(pets) == 1
    assert pets[0].name == "Рекс"


@pytest.mark.asyncio
async def test_get_pet_wrong_owner_returns_none(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=3, username="u3")
    service = PetService(PetRepository(db_session))
    pet = await service.create(owner_id=user.id, name="Пушок", species="rodent",
                               age_months=12, weight_kg=0.5, goal="maintain")
    result = await service.get_by_id(pet_id=pet.id, owner_id=999)
    assert result is None


@pytest.mark.asyncio
async def test_invalid_species_raises_error(db_session):
    user = await UserService(UserRepository(db_session)).get_or_create(telegram_id=4, username="u4")
    service = PetService(PetRepository(db_session))
    with pytest.raises(ValueError, match="invalid_species"):
        await service.create(owner_id=user.id, name="X", species="dragon",
                             age_months=1, weight_kg=1.0, goal="maintain")
