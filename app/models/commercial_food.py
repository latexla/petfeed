from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommercialFood(Base):
    __tablename__ = "commercial_foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    species: Mapped[str] = mapped_column(String(20), nullable=False)
    food_type: Mapped[str] = mapped_column(String(20), nullable=False)  # dry|wet
    life_stage: Mapped[str] = mapped_column(String(20), server_default="all")  # junior|adult|senior|all
    breed_size: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mini|medium|large|all
    condition_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    kcal_per_100g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    protein_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fat_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    carb_g: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    calcium_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    phosphorus_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    omega3_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    taurine_mg: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(40), server_default="manufacturer")
    barcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
