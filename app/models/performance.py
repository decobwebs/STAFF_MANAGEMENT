# app/models/performance.py
from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from app.database import Base

class PerformanceScore(Base):
    __tablename__ = "performance_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)

    report_consistency = Column(Float, default=0.0)
    task_score = Column(Float, default=0.0)
    attendance_rate = Column(Float, default=0.0)
    training_score = Column(Float, default=0.0)
    achievement_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "month", "year", name="uq_user_month_year"),
    )