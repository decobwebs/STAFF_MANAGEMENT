from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, timezone
from app.database import get_db
from app.core.auth import get_current_user
from app.models.goal import Goal, GoalUpdate
from app.schemas.goal import (
    GoalCreate, GoalUpdateCreate, GoalResponse,
    GoalDetailResponse, GoalDashboardResponse, GoalUpdateResponse
)

router = APIRouter(prefix="/goals", tags=["goals"])

def get_goal_status(goal: Goal, latest_progress: int, today: date) -> str:
    if latest_progress == 100:
        return "achieved"
    elif goal.target_date < today:
        return "overdue"
    else:
        return "ongoing"

@router.post("", response_model=GoalResponse)
async def create_goal(
    goal_in: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    goal = Goal(
        user_id=current_user.id,
        title=goal_in.title,
        description=goal_in.description,
        frequency=goal_in.frequency,
        priority=goal_in.priority,
        target_date=goal_in.target_date
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    # Add initial update (0%)
    update = GoalUpdate(goal_id=goal.id, progress_percent=0, note="Goal created")
    db.add(update)
    await db.commit()

    return GoalResponse(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        frequency=goal.frequency,
        priority=goal.priority,
        target_date=goal.target_date,
        created_at=goal.created_at,
        latest_progress=0,
        status=get_goal_status(goal, 0, date.today())
    )

@router.post("/{goal_id}/update", response_model=GoalUpdateResponse)
async def add_goal_update(
    goal_id: int,
    update_in: GoalUpdateCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    goal = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    if not goal.scalar_one_or_none():
        raise HTTPException(404, "Goal not found")

    update = GoalUpdate(
        goal_id=goal_id,
        note=update_in.note,
        progress_percent=update_in.progress_percent
    )
    db.add(update)
    await db.commit()
    await db.refresh(update)
    return update

@router.get("/dashboard", response_model=GoalDashboardResponse)
async def get_goal_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    today = date.today()
    goals = await db.execute(
        select(Goal)
        .where(Goal.user_id == current_user.id)
        .order_by(Goal.target_date)
    )
    goal_list = goals.scalars().all()

    # Get latest progress for each goal
    achieved, ongoing, overdue = [], [], []
    for goal in goal_list:
        latest_update = await db.execute(
            select(GoalUpdate)
            .where(GoalUpdate.goal_id == goal.id)
            .order_by(GoalUpdate.created_at.desc())
            .limit(1)
        )
        latest = latest_update.scalar_one_or_none()
        progress = latest.progress_percent if latest else 0
        status = get_goal_status(goal, progress, today)

        resp = GoalResponse(
            id=goal.id,
            title=goal.title,
            description=goal.description,
            frequency=goal.frequency,
            priority=goal.priority,
            target_date=goal.target_date,
            created_at=goal.created_at,
            latest_progress=progress,
            status=status
        )

        if status == "achieved":
            achieved.append(resp)
        elif status == "overdue":
            overdue.append(resp)
        else:
            ongoing.append(resp)

    return GoalDashboardResponse(achieved=achieved, ongoing=ongoing, overdue=overdue)

@router.get("/{goal_id}", response_model=GoalDetailResponse)
async def get_goal_detail(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    goal = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal_obj = goal.scalar_one_or_none()
    if not goal_obj:
        raise HTTPException(404, "Goal not found")

    updates = await db.execute(
        select(GoalUpdate)
        .where(GoalUpdate.goal_id == goal_id)
        .order_by(GoalUpdate.created_at)
    )
    update_list = [GoalUpdateResponse.model_validate(u) for u in updates.scalars()]

    latest_progress = update_list[-1].progress_percent if update_list else 0
    status = get_goal_status(goal_obj, latest_progress, date.today())

    return GoalDetailResponse(
        id=goal_obj.id,
        title=goal_obj.title,
        description=goal_obj.description,
        frequency=goal_obj.frequency,
        priority=goal_obj.priority,
        target_date=goal_obj.target_date,
        created_at=goal_obj.created_at,
        latest_progress=latest_progress,
        status=status,
        updates=update_list
    )