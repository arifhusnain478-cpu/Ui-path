from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Float, JSON, String

from app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    case_id = Column(String, primary_key=True, index=True)
    jurisdiction = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="open")
    product_name = Column(String, nullable=False)
    batch_number = Column(String, nullable=True)
    complaint_type = Column(String, nullable=False)
    source_list = Column(JSON, nullable=False, default=list)
    override_reason = Column(String, nullable=True)


class ComplaintCreate(BaseModel):
    case_id: str = Field(..., pattern=r"^C-\d{3,}$")
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    status: Literal["open", "pending_review", "closed"] = "open"
    product_name: str
    batch_number: Optional[str] = None
    complaint_type: Literal["contamination", "labeling", "quality"]
    source_list: List[str] = []
    override_reason: Optional[str] = None


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    jurisdiction: Literal["US", "EU"]
    risk_level: Literal["low", "medium", "high", "critical"]
    confidence_score: float
    status: Literal["open", "pending_review", "closed"]
    product_name: str
    batch_number: Optional[str]
    complaint_type: Literal["contamination", "labeling", "quality"]
    source_list: List[str]
    override_reason: Optional[str]
