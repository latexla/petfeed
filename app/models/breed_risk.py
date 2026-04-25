from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BreedRisk(Base):
    __tablename__ = "breed_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    breed_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_key: Mapped[str] = mapped_column(String(50), nullable=False)
