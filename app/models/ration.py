from datetime import datetime
from sqlalchemy import Integer, String, Numeric, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Ration(Base):
    __tablename__ = "rations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(Integer, ForeignKey("pets.id", ondelete="CASCADE"))
    daily_calories: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    daily_food_grams: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    food_per_meal_grams: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
