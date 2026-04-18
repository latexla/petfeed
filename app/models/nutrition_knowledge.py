from sqlalchemy import Integer, String, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class NutritionKnowledge(Base):
    __tablename__ = "nutrition_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    rer_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    kcal_per_100g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    stop_foods: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
