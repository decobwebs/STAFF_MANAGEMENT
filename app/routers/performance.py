from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select
from app.database import get_db
from app.core.auth import get_current_user
from app.services.performance import calculate_performance_score
from app.models.performance import PerformanceScore

router = APIRouter(prefix="/performance", tags=["performance"])

@router.get("/my")
async def get_my_performance(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    now = datetime.utcnow()
    month, year = now.month, now.year

    # Check if score exists
    result = await db.execute(
        select(PerformanceScore)
        .where(PerformanceScore.user_id == current_user.id)
        .where(PerformanceScore.month == month)
        .where(PerformanceScore.year == year)
    )
    score = result.scalar_one_or_none()

    if not score:
        # Calculate on-the-fly (or trigger async calc in prod)
        calculated = await calculate_performance_score(db, current_user.id, month, year)
        score = PerformanceScore(
            user_id=current_user.id,
            month=month,
            year=year,
            score=calculated
        )
        db.add(score)
        await db.commit()
        await db.refresh(score)

    return {
        "score": round(score.score, 2),
        "breakdown": {
            "report_consistency": score.report_consistency,
            "task_score": score.task_score,
            "attendance_rate": score.attendance_rate,
            "training_score": score.training_score,
            "achievement_count": score.achievement_count
        }
    }