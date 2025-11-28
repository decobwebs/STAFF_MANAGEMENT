from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from datetime import date

class ReportCreate(BaseModel):
    achievements: str = Field(..., min_length=1, description="Rich text: HTML or markdown")
    challenges: str = Field(..., min_length=1)
    completed_tasks: str = Field(..., min_length=1)
    plans_for_tomorrow: str = Field(..., min_length=1)

class ReportUpdate(BaseModel):
    achievements: str = Field(..., min_length=1)
    challenges: str = Field(..., min_length=1)
    completed_tasks: str = Field(..., min_length=1)
    plans_for_tomorrow: str = Field(..., min_length=1)

class ReportResponse(BaseModel):
    id: int
    user_id: int
    date: datetime
    achievements: str
    challenges: str
    completed_tasks: str
    plans_for_tomorrow: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReportHistoryItem(BaseModel):
    date: date
    status: str  # "submitted" or "missed"
    achievements: Optional[str] = None
    challenges: Optional[str] = None
    completed_tasks: Optional[str] = None
    plans_for_tomorrow: Optional[str] = None

class ReportHistoryResponse(BaseModel):
    month: int
    year: int
    reports: List[ReportHistoryItem]