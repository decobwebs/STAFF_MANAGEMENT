from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=72)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    name: str | None  # ← Nullable in response
    role: str

    
    model_config = {"from_attributes": True}  # ✅ Pydantic v2 style

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse