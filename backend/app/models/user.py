from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Boolean, Column, String

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    @property
    def username(self):
        return self.full_name


class UserCreate(BaseModel):
    user_id: str = Field(..., pattern=r"^U-\d{3,}$")
    email: EmailStr
    password: str
    full_name: str
    role: Literal["reviewer", "admin", "qa_lead"]
    jurisdiction: Literal["US", "EU"]


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    full_name: str
    role: Literal["reviewer", "admin", "qa_lead"]
    jurisdiction: Literal["US", "EU"]
    is_active: bool
