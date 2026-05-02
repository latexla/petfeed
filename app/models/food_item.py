from sqlalchemy import Integer, String, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    kcal_per_100g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    protein_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fat_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    carb_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    calcium_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    phosphorus_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    omega3_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    taurine_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="USDA")
