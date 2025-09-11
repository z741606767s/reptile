from pydantic import BaseModel, EmailStr
from typing import Optional
from .base import BaseModelMixin


class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class User(UserBase, BaseModelMixin):
    is_active: bool = True

    class Config:
        from_attributes = True