from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, not_
from datetime import date, datetime, timedelta
from app.database import get_db
from app.core.auth import get_current_admin
from app.models.user import User
from app.models.report import DailyReport
from app.models.task import Task
from app.models.attendance import Attendance
from app.routers import goal
from app.schemas.admin import AdminReportStatusResponse, AdminStaffReportItem
from app.schemas.task import TaskResponse, TaskRate
from app.schemas.admin import AdminTaskCreate, AdminTaskFilter
from typing import List, Optional
from datetime import timezone
from app.schemas.admin import StaffProfileResponse
from app.models.goal import Goal, GoalUpdate
from app.schemas.goal import GoalDetailResponse, GoalUpdateResponse
from app.schemas.attendance import DailyAttendanceRecord, MonthlyAttendanceResponse
from app.schemas.report import ReportHistoryResponse, ReportHistoryItem
from datetime import date
from calendar import monthrange


router = APIRouter(prefix="/admin", tags=["admin"])



def get_goal_status(goal: Goal, latest_progress: int, today: date) -> str:
    if latest_progress == 100:
        return "achieved"
    elif goal.target_date < today:
        return "overdue"
    else:
        return "ongoing"




@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    today = date.today()
    now = datetime.now()

    # 1. Staff counts
    total_staff = await db.execute(
        select(func.count(User.id)).where(User.role == "staff")
    )
    total = total_staff.scalar_one()

    # Checked in today
    checked_in = await db.execute(
        select(func.count(Attendance.id))
        .join(User, User.id == Attendance.user_id)
        .where(User.role == "staff")
        .where(func.date(Attendance.check_in_at) == today)
    )
    checked_in_count = checked_in.scalar_one()

    not_checked_in_count = total - checked_in_count

    # 2. Reports (today only)
    submitted_reports = await db.execute(
        select(func.count(DailyReport.id))
        .where(func.date(DailyReport.date) == today)
    )
    submitted = submitted_reports.scalar_one()

    pending = not_checked_in_count  # staff who haven’t submitted report yet
    missed = 0  # For simplicity; calculate properly in Part 2

    # 3. Tasks
    total_tasks = await db.execute(select(func.count(Task.id)))
    completed_tasks = await db.execute(
        select(func.count(Task.id)).where(Task.status == "completed")
    )
    overdue_tasks = await db.execute(
        select(func.count(Task.id))
        .where(Task.status != "completed")
        .where(Task.deadline < now)
    )

    # 4. Top Workers (by hours this month — simplified)
    top_workers = []

    # 5. Top Performers (by task rating — simplified)
    top_performers = []

    return {
        "staff": {
            "total": total,
            "checked_in_today": checked_in_count,
            "not_checked_in_today": not_checked_in_count
        },
        "reports": {
            "submitted": submitted,
            "pending": pending,
            "missed": missed
        },
        "tasks": {
            "total": total_tasks.scalar_one(),
            "completed": completed_tasks.scalar_one(),
            "overdue": overdue_tasks.scalar_one()
        },
        "top_workers": top_workers,
        "top_performers": top_performers
    }



@router.get("/reports/status", response_model=AdminReportStatusResponse)
async def admin_report_status(
    report_date: date,
    status_filter: str = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Get all staff
    staff_result = await db.execute(
        select(User.id, User.name, User.email)
        .where(User.role == "staff")
    )
    staff_list = staff_result.fetchall()

    # Get submitted reports on report_date
    submitted_result = await db.execute(
        select(DailyReport.user_id)
        .where(func.date(DailyReport.date) == report_date)
    )
    submitted_ids = {row[0] for row in submitted_result.fetchall()}

    today = date.today()
    staff_data = []
    summary = {"submitted": 0, "pending": 0, "missed": 0}

    for staff in staff_list:
        staff_id, name, email = staff.id, staff.name, staff.email

        if staff_id in submitted_ids:
            status = "submitted"
        else:
            if report_date < today:
                status = "missed"
            else:
                status = "pending"

        # Apply status filter
        if status_filter and status != status_filter:
            continue

        staff_data.append(
            AdminStaffReportItem(
                id=staff_id,
                name=name,
                email=email,
                status=status
            )
        )
        summary[status] += 1

    return AdminReportStatusResponse(
        date=report_date,
        summary=summary,
        staff=staff_data
    )





@router.post("/tasks", response_model=TaskResponse)
async def admin_create_task(
    task_in: AdminTaskCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Verify assigned user exists and is staff
    assigned = await db.execute(
        select(User)
        .where(User.id == task_in.assigned_to_id)
        .where(User.role == "staff")
    )
    if not assigned.scalar_one_or_none():
        raise HTTPException(400, "Assigned user not found or not staff")

    # Admin can optionally rate — if not provided, use admin as rater
    rater_id = task_in.rater_id or admin.id

    task = Task(
        title=task_in.title,
        description=task_in.description,
        creator_id=admin.id,          # ← Admin is creator
        assigned_to_id=task_in.assigned_to_id,
        rater_id=rater_id,
        deadline=task_in.deadline,
        status="pending"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.post("/tasks/{task_id}/rate", response_model=TaskResponse)
async def admin_rate_task(
    task_id: int,
    rating_in: TaskRate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    task = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task_obj = task.scalar_one_or_none()
    if not task_obj:
        raise HTTPException(404, "Task not found")

    if task_obj.status != "completed":
        raise HTTPException(400, "Task must be completed before rating")

    task_obj.rating = rating_in.rating
    db.add(task_obj)
    await db.commit()
    await db.refresh(task_obj)
    return task_obj

@router.get("/tasks", response_model=List[TaskResponse])
async def admin_list_tasks(
    filters: AdminTaskFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    query = select(Task)

    if filters.assigned_to_id:
        query = query.where(Task.assigned_to_id == filters.assigned_to_id)
    if filters.status:
        query = query.where(Task.status == filters.status)
    if filters.overdue is not None:
        now = datetime.now(timezone.utc)
        if filters.overdue:
            query = query.where(Task.status != "completed").where(Task.deadline < now)
        else:
            query = query.where(
                (Task.status == "completed") | (Task.deadline >= now)
            )
    if filters.date_from:
        query = query.where(Task.created_at >= filters.date_from)
    if filters.date_to:
        query = query.where(Task.created_at <= filters.date_to)

    result = await db.execute(query.order_by(Task.deadline))
    return result.scalars().all()






@router.get("/staff/{user_id}", response_model=StaffProfileResponse)
async def admin_get_staff_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # 1. Get user
    user = await db.execute(
        select(User).where(User.id == user_id, User.role == "staff")
    )
    staff = user.scalar_one_or_none()
    if not staff:
        raise HTTPException(404, "Staff not found")

    # 2. Attendance: total hours this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    attendance_records = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == user_id)
        .where(Attendance.check_in_at >= month_start)
        .where(Attendance.check_out_at.isnot(None))
    )
    total_seconds = 0
    for rec in attendance_records.scalars():
        if rec.check_out_at:
            total_seconds += (rec.check_out_at - rec.check_in_at).total_seconds()
    total_hours = round(total_seconds / 3600, 2)

    # 3. Reports (all)
    reports = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == user_id)
        .order_by(DailyReport.date.desc())
    )

    # 4. Tasks
    assigned_tasks = await db.execute(
        select(Task)
        .where(Task.assigned_to_id == user_id)
        .order_by(Task.deadline)
    )
    created_tasks = await db.execute(
        select(Task)
        .where(Task.creator_id == user_id)
        .order_by(Task.created_at.desc())
    )

    # 5. Goals
    goals = await db.execute(
        select(Goal)
        .where(Goal.user_id == user_id)
        .order_by(Goal.target_date)
    )
    goal_list = []
    today = date.today()
    for goal in goals.scalars():
        updates_result = await db.execute(
            select(GoalUpdate)
            .where(GoalUpdate.goal_id == goal.id)
            .order_by(GoalUpdate.created_at)
        )
        update_list = updates_result.scalars().all()

        latest_progress = update_list[-1].progress_percent if update_list else 0
        status = get_goal_status(goal, latest_progress, today)

        goal_with_updates = GoalDetailResponse(
            id=goal.id,
            title=goal.title,
            description=goal.description,
            frequency=goal.frequency,
            priority=goal.priority,
            target_date=goal.target_date,
            created_at=goal.created_at,
            latest_progress=latest_progress,
            status=status,
            updates=[GoalUpdateResponse.model_validate(u) for u in update_list]
        )
        goal_list.append(goal_with_updates)

    return StaffProfileResponse(
        id=staff.id,
        name=staff.name,
        email=staff.email,
        # date_of_birth=staff.date_of_birth,  # ← REMOVE THIS LINE
        role=staff.role,
        total_working_hours_this_month=total_hours,
        reports=reports.scalars().all(),
        assigned_tasks=assigned_tasks.scalars().all(),
        created_tasks=created_tasks.scalars().all(),
        goals=goal_list,
        achievements=[]
    )



@router.get("/staff", response_model=List[AdminStaffReportItem])
async def admin_list_staff(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """
    Returns list of all staff members (id, name, email) for task assignment.
    """
    staff_result = await db.execute(
        select(User.id, User.name, User.email)
        .where(User.role == "staff")
        .order_by(User.name)
    )
    staff_list = staff_result.fetchall()

    return [
        AdminStaffReportItem(
            id=row.id,
            name=row.name or "",  # in case name is NULL
            email=row.email,
            status=""  # not used here, but required by schema
        )
        for row in staff_list
    ]





@router.get("/staff/{user_id}/attendance", response_model=MonthlyAttendanceResponse)
async def admin_get_staff_attendance(
    user_id: int,
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Optional: verify user exists and is staff
    user_check = await db.execute(
        select(User).where(User.id == user_id, User.role == "staff")
    )
    if not user_check.scalar_one_or_none():
        raise HTTPException(404, "Staff not found")

    now = datetime.now(timezone.utc)
    if month is None:
        month = now.month
    if year is None:
        year = now.year

    if not (1 <= month <= 12):
        raise HTTPException(400, "Invalid month")
    if year < 1900 or year > 2100:
        raise HTTPException(400, "Invalid year")

    # Reuse your existing attendance logic (copy-paste for now, or refactor later)
    num_days = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)

    result = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == user_id)
        .where(func.date(Attendance.check_in_at) >= start_date)
        .where(func.date(Attendance.check_in_at) <= end_date)
        .order_by(Attendance.check_in_at)
    )
    records = result.scalars().all()

    record_map = {}
    total_minutes = 0
    for rec in records:
        rec_date = rec.check_in_at.date()
        record_map[rec_date] = rec
        if rec.check_out_at:
            total_minutes += int((rec.check_out_at - rec.check_in_at).total_seconds() // 60)

    days = []
    current = start_date
    now_utc = datetime.now(timezone.utc)
    while current <= end_date:
        if current in record_map:
            rec = record_map[current]
            is_late = rec.check_in_at.time() > datetime.strptime("07:00", "%H:%M").time()
            if rec.check_out_at:
                status = "completed"
                total_work_minutes = int((rec.check_out_at - rec.check_in_at).total_seconds() // 60)
                missed_checkout = False
                is_late_checkout = rec.check_out_at.time() > datetime.strptime("20:00", "%H:%M").time()
            else:
                status = "checked_in_only"
                total_work_minutes = None
                is_late_checkout = False
                missed_checkout = (current == now_utc.date() and now_utc.time() >= datetime.strptime("20:00", "%H:%M").time()) or (current < now_utc.date())
            days.append(
                DailyAttendanceRecord(
                    date=current,
                    status=status,
                    check_in_time=rec.check_in_at,
                    check_out_time=rec.check_out_at,
                    total_work_time_minutes=total_work_minutes,
                    is_late=is_late,
                    is_late_checkout=is_late_checkout,
                    missed_checkout=missed_checkout
                )
            )
        else:
            days.append(
                DailyAttendanceRecord(
                    date=current,
                    status="absent",
                    check_in_time=None,
                    check_out_time=None,
                    total_work_time_minutes=None,
                    is_late=False,
                    is_late_checkout=False,
                    missed_checkout=False
                )
            )
        current += timedelta(days=1)

    total_hours = round(total_minutes / 60, 2)
    return MonthlyAttendanceResponse(month=month, year=year, total_work_hours=total_hours, days=days)


@router.get("/staff/{user_id}/reports", response_model=ReportHistoryResponse)
async def admin_get_staff_reports(
    user_id: int,
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    # Verify staff exists
    user_check = await db.execute(
        select(User).where(User.id == user_id, User.role == "staff")
    )
    if not user_check.scalar_one_or_none():
        raise HTTPException(404, "Staff not found")

    now = datetime.now()
    if month is None:
        month = now.month
    if year is None:
        year = now.year

    if not (1 <= month <= 12):
        raise HTTPException(400, "Invalid month")
    if year < 1900 or year > 2100:
        raise HTTPException(400, "Invalid year")

    # Get first report
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
    start_of_month = date(year, month, 1)
    today = now.date()
    end_of_month = date(year, month, monthrange(year, month)[1])
    report_start = max(first_date, start_of_month)
    report_end = min(end_of_month, today)

    if report_start > report_end:
        return ReportHistoryResponse(month=month, year=year, reports=[])

    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == user_id)
        .where(func.date(DailyReport.date) >= report_start)
        .where(func.date(DailyReport.date) <= report_end)
    )
    reports = result.scalars().all()
    report_map = {r.date.date(): r for r in reports}

    report_list = []
    current = report_start
    while current <= report_end:
        if current in report_map:
            r = report_map[current]
            item = ReportHistoryItem(
                date=current,
                status="submitted",
                achievements=r.achievements,
                challenges=r.challenges,
                completed_tasks=r.completed_tasks,
                plans_for_tomorrow=r.plans_for_tomorrow
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

    return ReportHistoryResponse(month=month, year=year, reports=report_list)