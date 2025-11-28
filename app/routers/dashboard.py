from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.report import DailyReport
from app.models.task import Task
from app.data.staff import staff_birthdays

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def find_next_birthday(staff_list):
    today = date.today()
    candidates = []
    for person in staff_list:
        dob_str = person["date_of_birth"]
        dob = date.fromisoformat(dob_str)
        try:
            # Try to use Feb 29 in non-leap years → fails
            bday_this_year = dob.replace(year=today.year)
        except ValueError:
            # Handle Feb 29 → use Feb 28 instead
            if dob.month == 2 and dob.day == 29:
                bday_this_year = date(today.year, 2, 28)
            else:
                continue  # skip invalid dates

        if bday_this_year < today:
            # Move to next year
            try:
                bday_this_year = dob.replace(year=today.year + 1)
            except ValueError:
                if dob.month == 2 and dob.day == 29:
                    bday_this_year = date(today.year + 1, 2, 28)
                else:
                    continue

        candidates.append((bday_this_year, person))
    
    if not candidates:
        return None
    return min(candidates, key=lambda x: x[0])[1]

@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1. Find next birthday
    next_birthday = find_next_birthday(staff_birthdays)

    # 2. Get today's report status
    today = datetime.utcnow().date()
    report = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == current_user.id)
        .where(func.date(DailyReport.created_at) == today)
    )
    report_status = "submitted" if report.scalar_one_or_none() else "pending"

    # 3. Count uncompleted tasks
    uncompleted = await db.execute(
        select(func.count(Task.id))
        .where(Task.assigned_to_id == current_user.id)
        .where(Task.status != "completed")
    )
    uncompleted_count = uncompleted.scalar_one() or 0

    return {
        "next_birthday": next_birthday,
        "current_user": {
            "name": current_user.name or current_user.email.split("@")[0],
            "report_status": report_status,
            "uncompleted_tasks": uncompleted_count
        }
    }