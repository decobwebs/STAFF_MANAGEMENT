from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Date
from app.database import Base

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String, nullable=False)  # daily, weekly, etc.
    priority = Column(String, nullable=False)   # low, medium, high
    target_date = Column(Date, nullable=False)  # auto-calculated or set
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GoalUpdate(Base):
    __tablename__ = "goal_updates"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    note = Column(Text, nullable=True)
    progress_percent = Column(Integer, nullable=False)  # 0–100
    created_at = Column(DateTime(timezone=True), server_default=func.now())