from sqlalchemy import Integer, String, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    food_type: Mapped[str] = mapped_column(String(50), nullable=False)  # dry|wet|natural|raw
    kcal_per_100g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    protein_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fat_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fiber_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
