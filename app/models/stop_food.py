from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class StopFood(Base):
    __tablename__ = "stop_foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    species: Mapped[str] = mapped_column(String(50), nullable=False)  # dog|cat|all
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1|2|3
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    toxic_component: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
