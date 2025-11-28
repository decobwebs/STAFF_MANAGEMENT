from pydantic import BaseModel
from datetime import date
from typing import List, Optional
from .task import TaskCreate as BaseTaskCreate, TaskResponse
from .report import ReportResponse
from .goal import GoalDetailResponse



class AdminStaffReportItem(BaseModel):
    id: int
    name: Optional[str]
    email: str
    status: str  # "submitted", "pending", "missed"

class AdminReportStatusResponse(BaseModel):
    date: date
    summary: dict
    staff: List[AdminStaffReportItem]





class AdminTaskCreate(BaseTaskCreate):
    # Inherits title, description, deadline, priority
    assigned_to_id: int  # staff user ID
    # Admin is always creator & rater (optional)

class AdminTaskFilter(BaseModel):
    assigned_to_id: Optional[int] = None
    status: Optional[str] = None
    overdue: Optional[bool] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None




class StaffProfileResponse(BaseModel):
    id: int
    name: Optional[str]
    email: str
    # date_of_birth: Optional[date]  # ← COMMENT OUT OR REMOVE
    role: str
    total_working_hours_this_month: float
    reports: List[ReportResponse]
    assigned_tasks: List[TaskResponse]
    created_tasks: List[TaskResponse]
    goals: List[GoalDetailResponse]
    achievements: List[str] = []

    model_config = {"from_attributes": True}