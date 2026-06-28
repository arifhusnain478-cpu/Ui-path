from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Float, String, Text

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, index=True)
    jurisdiction = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    assigned_to = Column(String, nullable=True)
    current_stage = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    override_reason = Column(String, nullable=True)
    investigation_output = Column(Text, nullable=True)
    sla_deadline = Column(DateTime, nullable=True)


class CaseCreate(BaseModel):
    case_id: str = Field(..., pattern=r"^C-\d{3,}$")
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"] = "open"
    assigned_to: Optional[str] = None
    current_stage: str
    override_reason: Optional[str] = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"]
    assigned_to: Optional[str]
    current_stage: str
    created_at: datetime
    updated_at: datetime
    override_reason: Optional[str]
