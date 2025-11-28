from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.core.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdateStatus, TaskRate, TaskResponse, TaskSummaryResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskResponse)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # ✅ Validate deadline is in the future
    now = datetime.now(timezone.utc)
    if task_in.deadline <= now:
        raise HTTPException(400, "Deadline must be in the future")

    # Ensure assigned_to user exists
    assigned = await db.execute(select(User).where(User.id == task_in.assigned_to_id))
    if not assigned.scalar_one_or_none():
        raise HTTPException(400, "Assigned user not found")

    # Ensure rater exists (if provided)
    if task_in.rater_id:
        rater = await db.execute(select(User).where(User.id == task_in.rater_id))
        if not rater.scalar_one_or_none():
            raise HTTPException(400, "Rater user not found")

    # Create task
    task = Task(
        title=task_in.title,
        description=task_in.description,
        creator_id=current_user.id,
        assigned_to_id=task_in.assigned_to_id,
        rater_id=task_in.rater_id,
        deadline=task_in.deadline,
        status="pending"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task






@router.get("/me", response_model=TaskSummaryResponse)
async def get_my_tasks(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(Task)
        .where(Task.assigned_to_id == current_user.id)
        .order_by(Task.deadline)
    )
    tasks = result.scalars().all()

    # ✅ Use timezone-aware UTC for 'now'
    now = datetime.now(timezone.utc)

    completed = 0
    overdue = 0
    pending = 0

    for task in tasks:
        if task.status == "completed":
            completed += 1
        else:
            # Only consider deadline if task is not completed
            if task.deadline < now:
                overdue += 1
            else:
                pending += 1

    return TaskSummaryResponse(
        total_tasks=len(tasks),
        completed_tasks=completed,
        overdue_tasks=overdue,
        pending_tasks=pending,
        tasks=tasks
    )


@router.get("/created", response_model=list[TaskResponse])
async def get_my_created_tasks(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Tasks I created
    result = await db.execute(
        select(Task)
        .where(Task.creator_id == current_user.id)
        .order_by(Task.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .where(Task.assigned_to_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found or access denied")
    if task.status == "completed":
        raise HTTPException(400, "Task already completed")

    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/rate", response_model=TaskResponse)
async def rate_task(
    task_id: int,
    rating_in: TaskRate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .where(Task.rater_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found or you are not the rater")
    if task.status != "completed":
        raise HTTPException(400, "Task must be completed before rating")

    task.rating = rating_in.rating
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task