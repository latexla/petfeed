from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.weight_service import WeightService

router = APIRouter(prefix="/weight", tags=["weight"])


class WeightUpdate(BaseModel):
    pet_id: int
    weight_kg: float


class WeightUpdateResponse(BaseModel):
    pet_id: int
    old_weight: float
    new_weight: float
    ration_recalculated: bool


@router.post("", response_model=WeightUpdateResponse)
async def update_weight(data: WeightUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    if data.weight_kg <= 0:
        raise HTTPException(status_code=400, detail={"error": "invalid_weight"})
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=request.state.telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=data.pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    old_weight = float(pet.weight_kg)
    updated_pet, recalculated = await WeightService(db).update_weight(pet, data.weight_kg)
    return WeightUpdateResponse(
        pet_id=pet.id,
        old_weight=old_weight,
        new_weight=float(updated_pet.weight_kg),
        ration_recalculated=recalculated
    )
