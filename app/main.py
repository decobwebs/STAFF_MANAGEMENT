# app/main.py
from fastapi import FastAPI
from app.routers import auth
from app.database import engine
from app.models.user import User
from app.models.attendance import Attendance 
from app.routers import auth, attendance ,reports, task, performance, dashboard, goal, admin, admin_messages, message, announcements, chat
from app.models.performance import PerformanceScore 
from app.models.report import DailyReport
from app.models.task import Task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
import logging
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncEngine



app = FastAPI(title="SSMS - Smart Staff Management System", version="1.0")

# Include Routers
app.include_router(auth.router)
app.include_router(attendance.router)
app.include_router(reports.router)
app.include_router(task.router)
app.include_router(performance.router)
app.include_router(dashboard.router)
app.include_router(goal.router)
app.include_router(admin.router)
app.include_router(admin_messages.router)
app.include_router(announcements.router)
app.include_router(chat.router)

# Create DB Tables (for demo only — use Alembic in prod)
@app.on_event("startup")
async def startup_event():
    # create tables (async). ignore duplicate-object errors from previous partial runs.
    async with engine.begin() as conn:
        try:
            await conn.run_sync(User.metadata.create_all)
        except sa_exc.IntegrityError as e:
            msg = str(getattr(e, "orig", e))
            if "duplicate key value violates unique constraint" in msg or "already exists" in msg:
                logging.warning("Ignored duplicate DDL error during create_all: %s", msg)
            else:
                raise

@app.get("/")
def read_root():
    return {"message": "Welcome to SSMS Backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)