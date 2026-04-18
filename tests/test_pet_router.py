import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_pet_success(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/pets", json={
            "name": "Барсик", "species": "cat", "breed": "Мейн-кун",
            "age_months": 24, "weight_kg": 5.2, "goal": "maintain"
        }, headers={"X-Telegram-Id": "123456789"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Барсик"
    assert data["species"] == "cat"


@pytest.mark.asyncio
async def test_create_pet_invalid_species(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/pets", json={
            "name": "Дракон", "species": "dragon",
            "age_months": 1, "weight_kg": 1.0
        }, headers={"X-Telegram-Id": "123456789"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_pets_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/pets")
    assert response.status_code == 401
