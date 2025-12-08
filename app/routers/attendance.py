from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.database import get_db
from app.core.auth import get_current_user
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceResponse, AttendanceStatusResponse, MonthlyAttendanceResponse, DailyAttendanceRecord
from app.config import settings
from datetime import datetime, timezone, date, timedelta
from calendar import monthrange


router = APIRouter(prefix="/attendance", tags=["attendance"])

def get_client_ip(request: Request) -> str:
    """
    Get client IP from trusted header (X-Real-IP) set by your frontend.
    Falls back to X-Forwarded-For, then request.client.host.
    """
    # Priority 1: Your trusted custom header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Priority 2: Standard proxy header
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fallback: Direct connection
    return request.client.host

@router.get("/status", response_model=AttendanceStatusResponse)
async def get_attendance_status(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Get today's date (UTC)
    today = datetime.now(timezone.utc).date()

    # Fetch today's attendance record
    result = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == current_user.id)
        .where(func.date(Attendance.check_in_at) == today)
    )
    record = result.scalar_one_or_none()

    if not record:
        return AttendanceStatusResponse(status="not_checked_in")

    if record.check_out_at is None:
        return AttendanceStatusResponse(
            status="checked_in",
            check_in_time=record.check_in_at
        )
    else:
        # Calculate total work time in minutes
        duration = record.check_out_at - record.check_in_at
        total_minutes = int(duration.total_seconds() // 60)
        return AttendanceStatusResponse(
            status="checked_out",
            check_in_time=record.check_in_at,
            check_out_time=record.check_out_at,
            total_work_time_minutes=total_minutes
        )
    

@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Check if already checked in today
    today = func.date(func.now())
    existing = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == current_user.id)
        .where(func.date(Attendance.check_in_at) == today)
    )
    record = existing.scalar_one_or_none()
    if record:
        if record.check_out_at is None:
            raise HTTPException(400, "Already checked in today. Please check out first.")
        else:
            raise HTTPException(400, "Already completed attendance for today.")

    # Handle IP whitelist
    client_ip = get_client_ip(request)
    allowed_ips = settings.allowed_ips
    if allowed_ips is not None and client_ip not in allowed_ips:
        raise HTTPException(403, f"IP {client_ip} not allowed for check-in")

    # Create check-in record
    new_attendance = Attendance(
        user_id=current_user.id,
        check_in_at=datetime.now(),
        method="IP",
        ip_address=client_ip
    )
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return new_attendance


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Find today's open check-in (no checkout yet)
    today = func.date(func.now())
    existing = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == current_user.id)
        .where(func.date(Attendance.check_in_at) == today)
        .where(Attendance.check_out_at.is_(None))
    )
    record = existing.scalar_one_or_none()
    if not record:
        raise HTTPException(400, "No active check-in found for today. Please check in first.")

    record.check_out_at = datetime.now()
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/history", response_model=MonthlyAttendanceResponse)
async def get_attendance_history(
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Default to current month/year
    now = datetime.now(timezone.utc)
    if month is None:
        month = now.month
    if year is None:
        year = now.year

    # Validate month/year
    if not (1 <= month <= 12):
        raise HTTPException(400, "Invalid month")
    if year < 1900 or year > 2100:
        raise HTTPException(400, "Invalid year")

    # Get number of days in the month
    num_days = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)

    # Fetch all attendance records for the month
    result = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == current_user.id)
        .where(func.date(Attendance.check_in_at) >= start_date)
        .where(func.date(Attendance.check_in_at) <= end_date)
        .order_by(Attendance.check_in_at)
    )
    records = result.scalars().all()

    # Build a map: date -> record
    record_map = {}
    total_minutes = 0
    for rec in records:
        rec_date = rec.check_in_at.date()
        record_map[rec_date] = rec
        if rec.check_out_at:
            duration = rec.check_out_at - rec.check_in_at
            total_minutes += int(duration.total_seconds() // 60)

    # Build full month calendar
        # Build full month calendar
        # Build full month calendar
    days = []
    current = start_date
    now_utc = datetime.now(timezone.utc)
    while current <= end_date:
        if current in record_map:
            rec = record_map[current]
            check_in_time = rec.check_in_at

            # Late check-in: after 7:00 AM
            is_late = check_in_time.time() > datetime.strptime("07:00", "%H:%M").time()

            if rec.check_out_at:
                status = "completed"
                duration = rec.check_out_at - rec.check_in_at
                total_work_minutes = int(duration.total_seconds() // 60)
                missed_checkout = False
                is_late_checkout = rec.check_out_at.time() > datetime.strptime("20:00", "%H:%M").time()
            else:
                status = "checked_in_only"
                total_work_minutes = None
                is_late_checkout = False
                # Missed checkout if past 8 PM today, or any past day without checkout
                if current == now_utc.date():
                    missed_checkout = now_utc.time() >= datetime.strptime("20:00", "%H:%M").time()
                else:
                    missed_checkout = True

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
            # 👉 Absent: no check-in at all on this day
            days.append(
                DailyAttendanceRecord(
                    date=current,
                    status="absent",  # 👈 explicitly mark as absent
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

    return MonthlyAttendanceResponse(
        month=month,
        year=year,
        total_work_hours=total_hours,
        days=days
    )