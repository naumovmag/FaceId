from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=1, max_length=255)


class User(UserBase):
    id: int
    is_admin: bool = False
    is_active: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
