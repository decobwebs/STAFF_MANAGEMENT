from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.database import Base

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Structured rich-text fields (store as HTML or markdown)
    achievements = Column(Text, nullable=False)
    challenges = Column(Text, nullable=False)
    completed_tasks = Column(Text, nullable=False)
    plans_for_tomorrow = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())