from datetime import date
from sqlalchemy import Integer, Numeric, SmallInteger, String, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FeedingSession(Base):
    __tablename__ = "feeding_sessions"
    __table_args__ = (
        UniqueConstraint("pet_id", "session_date", name="uq_feeding_sessions_pet_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(Integer, ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_kcal: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    protein_g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    fat_g: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    calcium_pct: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    phosphorus_pct: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    taurine_pct: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    omega3_pct: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    kcal_pct: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    quality: Mapped[str] = mapped_column(String(10), nullable=False)
    tips: Mapped[str | None] = mapped_column(Text, nullable=True)
