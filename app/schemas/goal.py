from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import List, Optional

class GoalCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    frequency: str = Field(..., pattern="^(daily|weekly|monthly|quarterly|biannually|annually)$")
    priority: str = Field(..., pattern="^(low|medium|high)$")
    target_date: date  # Can be auto-calculated on frontend or passed

class GoalUpdateCreate(BaseModel):
    note: Optional[str] = None
    progress_percent: int = Field(..., ge=0, le=100)

class GoalUpdateResponse(BaseModel):
    id: int
    note: Optional[str]
    progress_percent: int
    created_at: datetime

    model_config = {"from_attributes": True}

class GoalResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    frequency: str
    priority: str
    target_date: date
    created_at: datetime
    latest_progress: int
    status: str  # "achieved", "ongoing", "overdue"

    model_config = {"from_attributes": True}

class GoalDetailResponse(GoalResponse):
    updates: List[GoalUpdateResponse]

class GoalDashboardResponse(BaseModel):
    achieved: List[GoalResponse]
    ongoing: List[GoalResponse]
    overdue: List[GoalResponse]