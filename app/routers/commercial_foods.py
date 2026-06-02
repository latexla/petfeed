import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.commercial_food_repo import CommercialFoodRepository
from app.services.feature_flag_service import is_enabled

router = APIRouter(prefix="/commercial-foods", tags=["commercial-foods"])


def _serialize(cf) -> dict:
    return {
        "id": cf.id, "brand": cf.brand, "name": cf.name,
        "species": cf.species, "food_type": cf.food_type,
        "life_stage": cf.life_stage, "breed_size": cf.breed_size,
        "tags": json.loads(cf.condition_tags or "[]"),
        "kcal_per_100g": float(cf.kcal_per_100g),
        "protein_g": float(cf.protein_g), "fat_g": float(cf.fat_g),
        "carb_g": float(cf.carb_g),
    }


@router.get("")
async def list_foods(
    species: str,
    request: Request,
    food_type: str | None = None,
    life_stage: str | None = None,
    breed_size: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    if not await is_enabled("feature_food_catalog", db):
        raise HTTPException(status_code=403, detail={"error": "feature_disabled"})
    repo = CommercialFoodRepository(db)
    if q and len(q.strip()) >= 2:
        rows = await repo.search(q.strip(), species, limit=limit)
    else:
        rows = await repo.filter(species=species, food_type=food_type,
                                 life_stage=life_stage, breed_size=breed_size,
                                 tag=tag, limit=limit, offset=offset)
    return [_serialize(cf) for cf in rows]
