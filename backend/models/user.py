from sqlmodel import Field, SQLModel
from typing import Optional
from enum import Enum
from datetime import datetime, timezone
from pydantic import EmailStr, field_validator
import re

class UserRole(str, Enum):
    customer = "Customer"
    waiter = "Waiter"
    chef = "Chef"
    manager = "Manager"

class UserBase(SQLModel):
    name: str = Field(index=True, min_length=2, max_length=100)
    email: EmailStr = Field(unique=True, index=True)
    phone: str = Field(unique=True, index=True, min_length=7, max_length=20)
    role: UserRole = Field(default=UserRole.customer)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        # Allow numbers starting optionally with '+'
        if not re.match(r"^\+?\d{7,20}$", v):
            raise ValueError("Numărul de telefon trebuie să conțină între 7 și 20 de cifre și poate începe cu '+'.")
        return v

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserRead(UserBase):
    id: int

class UserUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        if not re.match(r"^\+?\d{7,20}$", v):
            raise ValueError("Numărul de telefon trebuie să conțină între 7 și 20 de cifre și poate începe cu '+'.")
        return v

# Schemas for Tokens
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(SQLModel):
    email: Optional[str] = None
    role: Optional[str] = None
    table_id: Optional[int] = None
