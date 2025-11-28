from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    check_in_at = Column(DateTime(timezone=True), nullable=False)
    check_out_at = Column(DateTime(timezone=True), nullable=True)
    method = Column(String, nullable=False)  # "IP" or "QR"
    ip_address = Column(String, nullable=True)
    location = Column(String, nullable=True)
    device_info = Column(String, nullable=True)