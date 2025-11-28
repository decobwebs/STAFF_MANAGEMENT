from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    assigned_to_id: int
    rater_id: Optional[int] = None
    deadline: datetime

class TaskUpdateStatus(BaseModel):
    status: str  # "in_progress" or "completed"

class TaskRate(BaseModel):
    rating: int = Field(..., ge=1, le=5)

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    creator_id: int
    assigned_to_id: int
    rater_id: Optional[int]
    status: str
    rating: Optional[int]
    deadline: datetime
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TaskSummaryResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    pending_tasks: int
    tasks: List[TaskResponse]