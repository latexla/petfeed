from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.pet_repo import PetRepository
from app.services.user_service import UserService
from app.services.pet_service import PetService
from app.schemas.pet import PetCreate, PetUpdate, PetResponse

router = APIRouter(prefix="/pets", tags=["pets"])


async def _get_current_user(request: Request, db: AsyncSession):
    telegram_id = request.state.telegram_id
    return await UserService(UserRepository(db)).get_or_create(telegram_id=telegram_id)


@router.post("", response_model=PetResponse, status_code=201)
async def create_pet(data: PetCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request, db)
    try:
        pet = await PetService(PetRepository(db)).create(owner_id=user.id, **data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    return pet


@router.get("", response_model=list[PetResponse])
async def get_pets(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request, db)
    return await PetService(PetRepository(db)).get_by_owner(user.id)


@router.get("/{pet_id}", response_model=PetResponse)
async def get_pet(pet_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request, db)
    pet = await PetService(PetRepository(db)).get_by_id(pet_id=pet_id, owner_id=user.id)
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return pet


@router.put("/{pet_id}", response_model=PetResponse)
async def update_pet(pet_id: int, data: PetUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request, db)
    pet = await PetService(PetRepository(db)).update(
        pet_id=pet_id, owner_id=user.id,
        **{k: v for k, v in data.model_dump().items() if v is not None}
    )
    if pet is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return pet


@router.delete("/{pet_id}", status_code=204)
async def delete_pet(pet_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_current_user(request, db)
    deleted = await PetService(PetRepository(db)).delete(pet_id=pet_id, owner_id=user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
