import json

import pytest

from app.models.commercial_food import CommercialFood
from app.repositories.commercial_food_repo import CommercialFoodRepository


async def _add(db, **kw):
    defaults = dict(
        brand="Royal Canin", name="Sterilised 37", name_aliases=json.dumps(["sterilised"]),
        species="cat", food_type="dry", life_stage="adult", breed_size=None,
        condition_tags=json.dumps(["sterilised"]), kcal_per_100g=350,
        protein_g=37, fat_g=12, carb_g=30, source="manufacturer",
    )
    defaults.update(kw)
    cf = CommercialFood(**defaults)
    db.add(cf)
    await db.commit()
    return cf


@pytest.mark.asyncio
async def test_search_matches_alias_and_species(db_session):
    await _add(db_session, species="cat")
    await _add(db_session, brand="Pro Plan", name="Adult Dog", species="dog",
               name_aliases=json.dumps(["pro plan"]), condition_tags=json.dumps([]))
    repo = CommercialFoodRepository(db_session)
    hits = await repo.search("sterilised", "cat")
    assert len(hits) == 1
    assert hits[0].brand == "Royal Canin"


@pytest.mark.asyncio
async def test_filter_by_food_type(db_session):
    await _add(db_session, food_type="dry")
    await _add(db_session, name="Wet Cat", food_type="wet", name_aliases=json.dumps([]))
    repo = CommercialFoodRepository(db_session)
    dry = await repo.filter(species="cat", food_type="dry")
    assert len(dry) == 1
    assert dry[0].food_type == "dry"


from app.services.commercial_food_service import CommercialFoodService


@pytest.mark.asyncio
async def test_service_filter_returns_only_species(db_session):
    await _add(db_session, species="cat")
    await _add(db_session, brand="Pro Plan", name="Dog Adult", species="dog",
               name_aliases=json.dumps([]), condition_tags=json.dumps([]))
    repo = CommercialFoodRepository(db_session)
    svc = CommercialFoodService(repo)
    rows = await repo.filter(species="cat")
    ranked = svc.rank(rows, {"species": "cat", "life_stage": "adult",
                             "food_type": None, "breed_size": None, "tags": []})
    assert all(cf.species == "cat" for cf in ranked)
    assert len(ranked) == 1
