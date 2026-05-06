from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.models.user_feedback import UserFeedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    top_feature: str
    comment: str | None = None
    source: str = "manual"


@router.post("", status_code=201)
async def submit_feedback(data: FeedbackCreate, request: Request,
                          db: AsyncSession = Depends(get_db)):
    user = await UserService(UserRepository(db)).get_or_create(
        telegram_id=request.state.telegram_id
    )
    existing = (
        await db.execute(select(UserFeedback).where(UserFeedback.user_id == user.id))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"error": "already_submitted"})
    db.add(UserFeedback(
        user_id=user.id,
        rating=data.rating,
        top_feature=data.top_feature,
        comment=data.comment,
        source=data.source,
    ))
    await db.commit()
    return {"status": "ok"}
