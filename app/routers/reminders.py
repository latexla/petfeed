from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.reminder_repo import ReminderRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


class RemindersSet(BaseModel):
    pet_id: int
    times: list[str]


class ReminderResponse(BaseModel):
    id: int
    pet_id: int
    time_of_day: str

    model_config = {"from_attributes": True}


@router.post("", response_model=list[ReminderResponse], status_code=201)
async def set_reminders(data: RemindersSet, request: Request, db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=request.state.telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=data.pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    try:
        reminders = await ReminderService(ReminderRepository(db)).set_reminders(
            pet_id=pet.id, user_id=user.id, times=data.times
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    return reminders


@router.get("/{pet_id}", response_model=list[ReminderResponse])
async def get_reminders(pet_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(telegram_id=request.state.telegram_id)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return await ReminderService(ReminderRepository(db)).get_by_pet(pet.id)
