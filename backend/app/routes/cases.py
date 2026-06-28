from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.audit_event import AuditEvent, AuditEventCreate
from app.models.case import Case
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/cases", tags=["cases"])
security = HTTPBearer()

ALLOWED_TRANSITIONS = {
    "open": {"pending_review"},
    "pending_review": {"open"},
    "closed": set(),
}
VALID_STATUSES = {"open", "pending_review", "closed"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


class StatusUpdateRequest(BaseModel):
    status: str


class CaseStatusResponse(BaseModel):
    case_id: str
    status: str
    updated_at: datetime
    updated_by: str


class AuditEventResponse(BaseModel):
    event_id: str
    case_id: str
    timestamp: datetime
    action: str
    actor: str
    previous_value: Optional[str]
    new_value: Optional[str]
    override_reason: Optional[str]


@router.put("/{case_id}/status", response_model=CaseStatusResponse)
def update_case_status(
    case_id: str,
    body: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_status = body.status

    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{new_status}'. Allowed: {sorted(VALID_STATUSES)}",
        )

    case = db.query(Case).filter(Case.case_id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found")

    if new_status == "closed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cases cannot be closed via this endpoint. Use PUT /capa/{capa_id}/effectiveness.",
        )

    current_status = case.status
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transition from '{current_status}' to '{new_status}' is not allowed.",
        )

    case.status = new_status
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=case_id,
            actor=current_user.user_id,
            action="status_change",
            previous_value=current_status,
            new_value=new_status,
            override_reason=None,
        ),
    )

    return CaseStatusResponse(
        case_id=case.case_id,
        status=case.status,
        updated_at=case.updated_at,
        updated_by=current_user.user_id,
    )


@router.get("/{case_id}/audit", response_model=List[AuditEventResponse])
def get_case_audit_trail(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found")

    events = audit_service.get_audit_trail(db=db, case_id=case_id)

    return [
        AuditEventResponse(
            event_id=event.event_id,
            case_id=event.case_id,
            timestamp=event.timestamp,
            action=event.action,
            actor=event.actor,
            previous_value=event.previous_value,
            new_value=event.new_value,
            override_reason=event.override_reason,
        )
        for event in events
    ]
