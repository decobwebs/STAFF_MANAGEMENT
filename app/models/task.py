from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)      # Who created it
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who does it
    rater_id = Column(Integer, ForeignKey("users.id"), nullable=True)         # Who rates it
    status = Column(String, default="pending")  # pending, in_progress, completed
    rating = Column(Integer, nullable=True)     # 1–5
    deadline = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)