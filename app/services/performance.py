from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.report import DailyReport
from app.models.task import Task
from app.models.attendance import Attendance
from app.models.performance import PerformanceScore

async def get_report_consistency(db: AsyncSession, user_id: int, month: int, year: int) -> float:
    """% of days with reports in the month (max 100%)"""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    total_days = (end - start).days
    result = await db.execute(
        select(func.count(DailyReport.id))
        .where(DailyReport.user_id == user_id)
        .where(DailyReport.created_at >= start)
        .where(DailyReport.created_at < end)
    )
    submitted = result.scalar_one()
    return min((submitted / total_days) * 100, 100.0)

async def get_task_score(db: AsyncSession, user_id: int, month: int, year: int) -> float:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    result = await db.execute(
        select(func.avg(Task.rating))
        .where(Task.assigned_to_id == user_id)
        .where(Task.completed_at >= start)
        .where(Task.completed_at < end)
        .where(Task.rating.isnot(None))
    )
    avg_rating = result.scalar_one()

    # Convert Decimal to float or default to 0.0
    if avg_rating is None:
        avg_rating = 0.0
    else:
        avg_rating = float(avg_rating)

    return min(avg_rating * 20, 100.0)

async def get_attendance_rate(db: AsyncSession, user_id: int, month: int, year: int) -> float:
    """% of workdays with check-in (assume all days are workdays)"""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    total_days = (end - start).days
    result = await db.execute(
        select(func.count(Attendance.id))
        .where(Attendance.user_id == user_id)
        .where(func.date(Attendance.check_in_at) >= start.date())
        .where(func.date(Attendance.check_in_at) < end.date())
    )
    present = result.scalar_one()
    return min((present / total_days) * 100, 100.0)

async def get_training_score(db: AsyncSession, user_id: int, month: int, year: int) -> float:
    """Placeholder: return 100% for now"""
    return 100.0  # Implement when trainings module exists

async def get_achievement_count(db: AsyncSession, user_id: int, month: int, year: int) -> int:
    """Placeholder: return 0 for now"""
    return 0  # Implement when achievements module exists

async def calculate_performance_score(
    db: AsyncSession, user_id: int, month: int, year: int
) -> float:
    report = await get_report_consistency(db, user_id, month, year)
    task = await get_task_score(db, user_id, month, year)
    attendance = await get_attendance_rate(db, user_id, month, year)
    training = await get_training_score(db, user_id, month, year)
    achievements = await get_achievement_count(db, user_id, month, year)

    score = (
        report * 0.35 +
        task * 0.30 +
        attendance * 0.20 +
        training * 0.10 +
        min(achievements, 20) * 0.05  # Cap at 20 → 100%
    )
    return min(score, 100.0)