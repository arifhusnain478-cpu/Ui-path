from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, ForeignKey, JSON, String

from app.database import Base


class CAPA(Base):
    __tablename__ = "capas"

    capa_id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.case_id"), nullable=False, index=True)
    jurisdiction = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    root_cause = Column(String, nullable=False)
    corrective_action = Column(String, nullable=False)
    preventive_action = Column(String, nullable=False)
    source_list = Column(JSON, nullable=False, default=list)
    approved_by = Column(String, nullable=True)
    override_reason = Column(String, nullable=True)


class CAPACreate(BaseModel):
    capa_id: str = Field(..., pattern=r"^CAPA-\d{3,}$")
    case_id: str = Field(..., pattern=r"^C-\d{3,}$")
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"] = "open"
    root_cause: str
    corrective_action: str
    preventive_action: str
    source_list: List[str] = []
    override_reason: Optional[str] = None


class CAPAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    capa_id: str
    case_id: str
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"]
    root_cause: str
    corrective_action: str
    preventive_action: str
    source_list: List[str]
    approved_by: Optional[str]
    override_reason: Optional[str]
