from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.core.auth import get_current_user
from app.models.report import DailyReport
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse, ReportHistoryResponse, ReportHistoryItem
from calendar import monthrange
from datetime import date, timedelta, datetime 

today = datetime.now().date()

router = APIRouter(prefix="/reports", tags=["reports"])


# Helper function to fetch report history for any user
async def _get_report_history_for_user(
    db: AsyncSession,
    user_id: int,
    month: int,
    year: int
) -> ReportHistoryResponse:
    from datetime import datetime, date, timedelta
    from calendar import monthrange

    now = datetime.now()
    today = now.date()
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, monthrange(year, month)[1])
    report_end = min(end_of_month, today)

    # Check if user has any reports at all
    first_report = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == user_id)
        .order_by(DailyReport.date)
        .limit(1)
    )
    first = first_report.scalar_one_or_none()
    if not first:
        return ReportHistoryResponse(month=month, year=year, reports=[])

    first_date = first.date.date()
    report_start = max(first_date, start_of_month)

    if report_start > report_end:
        return ReportHistoryResponse(month=month, year=year, reports=[])

    # Fetch all reports in range
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == user_id)
        .where(func.date(DailyReport.date) >= first_date)
        .where(func.date(DailyReport.date) <= report_end)
    )
    all_reports = result.scalars().all()
    report_map = {rep.date.date(): rep for rep in all_reports}

    # Build timeline
    current = report_start
    report_list = []
    while current <= report_end:
        if current in report_map:
            rep = report_map[current]
            item = ReportHistoryItem(
                date=current,
                status="submitted",
                achievements=rep.achievements,
                challenges=rep.challenges,
                completed_tasks=rep.completed_tasks,
                plans_for_tomorrow=rep.plans_for_tomorrow
            )
        else:
            status = "missed" if current < today else "pending"
            item = ReportHistoryItem(
                date=current,
                status=status,
                achievements=None,
                challenges=None,
                completed_tasks=None,
                plans_for_tomorrow=None
            )
        report_list.append(item)
        current += timedelta(days=1)

    return ReportHistoryResponse(
        month=month,
        year=year,
        reports=report_list
    )

@router.post("", response_model=ReportResponse)
async def submit_report(
    report_in: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Check if report already exists for today
    today = datetime.now(timezone.utc).date()
    existing = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == current_user.id)
        .where(func.date(DailyReport.date) == today)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "You have already submitted a report today.")

    # Create new structured report
    report = DailyReport(
        user_id=current_user.id,
        achievements=report_in.achievements,
        challenges=report_in.challenges,
        completed_tasks=report_in.completed_tasks,
        plans_for_tomorrow=report_in.plans_for_tomorrow,
        date=datetime.now(timezone.utc)
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_in: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.id == report_id)
        .where(DailyReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found or access denied.")

    now = datetime.now(timezone.utc)
    if now - report.created_at > timedelta(hours=8):
        raise HTTPException(403, "You can only edit a report within 8 hours of submission.")

    # Update all fields
    report.achievements = report_in.achievements
    report.challenges = report_in.challenges
    report.completed_tasks = report_in.completed_tasks
    report.plans_for_tomorrow = report_in.plans_for_tomorrow
    report.updated_at = now

    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/me", response_model=list[ReportResponse])
async def get_my_reports(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == current_user.id)
        .order_by(DailyReport.created_at.desc())
    )
    return result.scalars().all()



@router.get("/history", response_model=ReportHistoryResponse)
async def get_report_history(
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    now = datetime.now()
    if month is None:
        month = now.month
    if year is None:
        year = now.year

    if not (1 <= month <= 12):
        raise HTTPException(400, "Invalid month")
    if year < 1900 or year > 2100:
        raise HTTPException(400, "Invalid year")

    # Find user's first ever report
    first_report = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == current_user.id)
        .order_by(DailyReport.date)
        .limit(1)
    )
    first = first_report.scalar_one_or_none()
    if not first:
        return ReportHistoryResponse(month=month, year=year, reports=[])

    first_date = first.date.date()
    start_of_month = date(year, month, 1)
    report_start = max(first_date, start_of_month)

    # Cap at today — no future dates
    today = now.date()
    end_of_month = date(year, month, monthrange(year, month)[1])
    report_end = min(end_of_month, today)

    if report_start > report_end:
        return ReportHistoryResponse(month=month, year=year, reports=[])

    # Fetch all reports from report_start to report_end
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == current_user.id)
        .where(func.date(DailyReport.date) >= report_start)
        .where(func.date(DailyReport.date) <= report_end)
    )
    all_reports = result.scalars().all()
    report_map = {rep.date.date(): rep for rep in all_reports}

    # Generate full timeline from report_start to report_end
    current = report_start
    report_list = []
    while current <= report_end:
        if current in report_map:
            rep = report_map[current]
            item = ReportHistoryItem(
                date=current,
                status="submitted",
                achievements=rep.achievements,
                challenges=rep.challenges,
                completed_tasks=rep.completed_tasks,
                plans_for_tomorrow=rep.plans_for_tomorrow
            )
        else:
            if current < today:
                # Past day with no report → missed
                item = ReportHistoryItem(
                    date=current,
                    status="missed",
                    achievements=None,
                    challenges=None,
                    completed_tasks=None,
                    plans_for_tomorrow=None
                )
            else:
                # Today (and no report yet) → pending
                item = ReportHistoryItem(
                    date=current,
                    status="pending",
                    achievements=None,
                    challenges=None,
                    completed_tasks=None,
                    plans_for_tomorrow=None
                )
        report_list.append(item)
        current += timedelta(days=1)

    return ReportHistoryResponse(
        month=month,
        year=year,
        reports=report_list
    )