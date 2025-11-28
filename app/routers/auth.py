# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.database import get_db
from app.utils.password import hash_password, verify_password
from app.core.security import create_access_token, create_refresh_token
from app.core.auth import get_current_user
from app.schemas.auth import ChangePasswordRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    try:
        hashed_pw = hash_password(user_in.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create user with name
    user = User(
        email=user_in.email,
        name=user_in.name,  # ← Save name
        hashed_password=hashed_pw
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Fetch user
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Return full token response
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )





@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user






@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # 2. Prevent reusing same password
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different"
        )

    # 3. Hash and update
    try:
        hashed_new = hash_password(request.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    current_user.hashed_password = hashed_new
    db.add(current_user)
    await db.commit()

    return {"message": "Password updated successfully"}