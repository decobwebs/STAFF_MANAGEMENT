from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

class AttendanceCreate(BaseModel):
    method: str  # "IP" or "QR"
    ip_address: Optional[str] = None
    location: Optional[str] = None
    device_info: Optional[str] = None

class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    check_in_at: datetime
    check_out_at: Optional[datetime]
    method: str
    ip_address: Optional[str]
    location: Optional[str]

    model_config = {"from_attributes": True}

class AttendanceStatusResponse(BaseModel):
    status: str  # "not_checked_in", "checked_in", "checked_out"
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    total_work_time_minutes: Optional[int] = None  # rounded to nearest minute


class DailyAttendanceRecord(BaseModel):
    date: date
    status: str  # "completed", "checked_in_only", "missed"
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    total_work_time_minutes: Optional[int] = None
    is_late: bool = False
    is_late_checkout: bool = False   
    missed_checkout: bool = False

class MonthlyAttendanceResponse(BaseModel):
    month: int
    year: int
    total_work_hours: float  # rounded to 2 decimals
    days: List[DailyAttendanceRecord]