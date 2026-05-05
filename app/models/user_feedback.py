from datetime import datetime
from sqlalchemy import Integer, SmallInteger, String, Text, DateTime, ForeignKey, UniqueConstraint, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_feedback_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    top_feature: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), server_default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
