from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, String

from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    previous_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    override_reason = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)


class AuditEventCreate(BaseModel):
    case_id: str = Field(..., pattern=r"^C-\d{3,}$")
    actor: str
    action: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    override_reason: Optional[str] = None


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    case_id: str
    actor: str
    action: str
    previous_value: Optional[str]
    new_value: Optional[str]
    override_reason: Optional[str]
    timestamp: datetime
