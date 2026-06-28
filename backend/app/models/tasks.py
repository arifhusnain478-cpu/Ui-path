from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, String

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)
    jurisdiction = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    assigned_to = Column(String, nullable=True)
    task_type = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    override_reason = Column(String, nullable=True)


class TaskCreate(BaseModel):
    task_id: str = Field(..., pattern=r"^T-\d{3,}$")
    case_id: str = Field(..., pattern=r"^C-\d{3,}$")
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"] = "open"
    assigned_to: Optional[str] = None
    task_type: str
    due_at: Optional[datetime] = None
    override_reason: Optional[str] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    case_id: str
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"]
    assigned_to: Optional[str]
    task_type: str
    due_at: Optional[datetime]
    completed_at: Optional[datetime]
    override_reason: Optional[str]
