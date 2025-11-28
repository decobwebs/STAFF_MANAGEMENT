from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.message import Announcement
from app.schemas.message import AnnouncementResponse
from typing import List

router = APIRouter(prefix="/announcements", tags=["announcements"])

@router.get("", response_model=List[AnnouncementResponse])
async def get_announcements(
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint: Get all announcements (no auth required)
    """
    result = await db.execute(
        select(Announcement)
        .order_by(Announcement.created_at.desc())
    )
    return result.scalars().all()