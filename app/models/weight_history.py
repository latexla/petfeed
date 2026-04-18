from datetime import datetime
from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class WeightHistory(Base):
    __tablename__ = "weight_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(Integer, ForeignKey("pets.id", ondelete="CASCADE"))
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
