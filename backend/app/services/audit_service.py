from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent, AuditEventCreate


def create_audit_event(db: Session, event: AuditEventCreate) -> AuditEvent:
    event_id = f"E-{uuid4().hex[:8]}"
    db_event = AuditEvent(
        event_id=event_id,
        case_id=event.case_id,
        actor=event.actor,
        action=event.action,
        previous_value=event.previous_value,
        new_value=event.new_value,
        override_reason=event.override_reason,
        timestamp=datetime.utcnow(),
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_audit_trail(db: Session, case_id: str) -> list[AuditEvent]:
    return (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.timestamp.asc())
        .all()
    )
