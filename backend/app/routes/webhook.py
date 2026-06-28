from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_event import AuditEvent, AuditEventCreate
from app.models.case import Case
from app.services import audit_service

router = APIRouter(prefix="/webhook", tags=["webhook"])

VALID_EVENT_TYPES = {
    "stage_change", "task_assigned", "task_completed", "sla_breach",
    "batch_hold_triggered", "case_escalated", "case_resumed",
    "investigation_started", "investigation_completed", "capa_triggered",
    "capa_completed", "closure_triggered", "system_event",
}

VALID_STAGES = {
    "intake", "risk_assessment", "human_review", "auto_investigation",
    "capa", "effectiveness_review", "closure", "paused", "escalated",
}

STAGE_TO_STATUS = {
    "human_review": "pending_review",
    "paused": "pending_review",
    "escalated": "pending_review",
    "intake": "open",
    "risk_assessment": "open",
    "auto_investigation": "open",
    "capa": "open",
    "effectiveness_review": "open",
}


class MaestroWebhookPayload(BaseModel):
    case_id: str
    event_type: str
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    actor: str
    timestamp: datetime
    payload: Optional[Dict[str, Any]] = None

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("case_id must not be empty")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in VALID_EVENT_TYPES:
            raise ValueError(f"event_type '{v}' not recognised. Allowed: {sorted(VALID_EVENT_TYPES)}")
        return v

    @field_validator("from_stage")
    @classmethod
    def validate_from_stage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STAGES:
            raise ValueError(f"from_stage '{v}' not recognised. Allowed: {sorted(VALID_STAGES)}")
        return v

    @field_validator("to_stage")
    @classmethod
    def validate_to_stage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STAGES:
            raise ValueError(f"to_stage '{v}' not recognised. Allowed: {sorted(VALID_STAGES)}")
        return v

    @field_validator("actor")
    @classmethod
    def validate_actor(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("actor must not be empty")
        return v


class MaestroWebhookResponse(BaseModel):
    received: bool
    event_id: str
    case_id: str
    event_type: str
    recorded_at: datetime
    message: str


@router.post("/maestro", response_model=MaestroWebhookResponse, status_code=status.HTTP_200_OK)
def receive_maestro_event(
    body: MaestroWebhookPayload,
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.case_id == body.case_id).first()
    case_exists = case is not None

    # Build summary
    if body.from_stage and body.to_stage:
        summary = f"Maestro: '{body.from_stage}'→'{body.to_stage}' for case '{body.case_id}' | actor: {body.actor}"
    elif body.to_stage:
        summary = f"Maestro event '{body.event_type}': case '{body.case_id}' entered '{body.to_stage}' | actor: {body.actor}"
    else:
        summary = f"Maestro event '{body.event_type}' for case '{body.case_id}' | actor: {body.actor}"

    if not case_exists:
        summary = f"[UNKNOWN CASE] {summary}"

    # Write to audit trail using the real audit_service signature
    audit_event = audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=body.case_id,
            actor=body.actor,
            action=f"maestro_{body.event_type}",
            previous_value=body.from_stage,
            new_value=body.to_stage,
            override_reason=None,
        ),
    )

    # Sync case status if applicable
    if case_exists and body.event_type == "stage_change" and body.to_stage:
        new_status = STAGE_TO_STATUS.get(body.to_stage)
        if new_status and case.status != new_status and case.status != "closed":
            case.status = new_status
            case.updated_at = datetime.utcnow()
            db.commit()

            audit_service.create_audit_event(
                db=db,
                event=AuditEventCreate(
                    case_id=body.case_id,
                    actor=body.actor,
                    action="status_synced_from_maestro",
                    previous_value=case.status,
                    new_value=new_status,
                    override_reason=None,
                ),
            )

    return MaestroWebhookResponse(
        received=True,
        event_id=audit_event.event_id,
        case_id=body.case_id,
        event_type=body.event_type,
        recorded_at=datetime.utcnow(),
        message=(
            f"Event '{body.event_type}' for case '{body.case_id}' recorded in audit trail."
            + ("" if case_exists else " Warning: case not found in backend database.")
        ),
    )
