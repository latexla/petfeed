from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.repositories.breed_repo import BreedRepository
from app.services.breed_service import BreedService

router = APIRouter(prefix="/breeds", tags=["breeds"])


class BreedCandidateOut(BaseModel):
    breed_id: int
    canonical_name: str
    canonical_name_ru: str
    score: float


class BreedMatchOut(BaseModel):
    confidence: str
    candidates: list[BreedCandidateOut]
    raw_input: str


@router.get("", response_model=BreedMatchOut)
async def search_breeds(species: str, q: str, db: AsyncSession = Depends(get_db)):
    if species not in ("dog", "cat"):
        raise HTTPException(status_code=422, detail="species must be 'dog' or 'cat'")
    service = BreedService(BreedRepository(db))
    result = await service.match_text(q, species)
    return BreedMatchOut(
        confidence=result.confidence,
        candidates=[
            BreedCandidateOut(
                breed_id=c.breed_id,
                canonical_name=c.canonical_name,
                canonical_name_ru=c.canonical_name_ru,
                score=c.score,
            )
            for c in result.candidates
        ],
        raw_input=result.raw_input,
    )


@router.post("/recognize-photo", response_model=BreedMatchOut)
async def recognize_breed_photo(
    species: str = Form(...),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if species not in ("dog", "cat"):
        raise HTTPException(status_code=422, detail="species must be 'dog' or 'cat'")
    photo_bytes = await photo.read()
    service = BreedService(BreedRepository(db))
    result = await service.recognize_from_photo(photo_bytes, species)
    return BreedMatchOut(
        confidence=result.confidence,
        candidates=[
            BreedCandidateOut(
                breed_id=c.breed_id,
                canonical_name=c.canonical_name,
                canonical_name_ru=c.canonical_name_ru,
                score=c.score,
            )
            for c in result.candidates
        ],
        raw_input=result.raw_input,
    )
