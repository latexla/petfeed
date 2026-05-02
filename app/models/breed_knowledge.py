from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BreedKnowledge(Base):
    __tablename__ = "breed_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    canonical_name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    weight_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    key_risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    adult_meals_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    full_content: Mapped[str] = mapped_column(Text, nullable=False)
