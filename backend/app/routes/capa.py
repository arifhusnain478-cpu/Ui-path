from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.audit_event import AuditEventCreate
from app.models.capa import CAPA
from app.models.case import Case
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/capa", tags=["capa"])
security = HTTPBearer()

VALID_EFFECTIVENESS_RESULTS = {"pass", "fail"}
VALID_ACTION_TYPES = {"corrective", "preventive"}


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


class CAPAActionItem(BaseModel):
    description: str
    type: str
    responsible_role: str
    due_date: str
    evidence_required: str
    effectiveness_metric: str
    source_citations: List[str]


class CAPACreateRequest(BaseModel):
    case_id: str
    actions: List[CAPAActionItem]
    notes: Optional[str] = None


class CAPACreateResponse(BaseModel):
    capa_id: str
    case_id: str
    actions: List[Dict[str, Any]]
    status: str
    created_at: datetime
    created_by: str


class EffectivenessRequest(BaseModel):
    result: str
    reviewer_notes: Optional[str] = None
    evidence_summary: Optional[str] = None


class EffectivenessResponse(BaseModel):
    capa_id: str
    case_id: str
    effectiveness_result: str
    reviewed_at: datetime
    reviewed_by: str
    case_status: str


@router.post("", response_model=CAPACreateResponse, status_code=status.HTTP_201_CREATED)
def create_capa(
    body: CAPACreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.case_id == body.case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{body.case_id}' not found")

    if case.status == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Case '{body.case_id}' is already closed.")

    if not body.actions:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="actions list must not be empty")

    for i, action in enumerate(body.actions):
        if action.type not in VALID_ACTION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"actions[{i}].type '{action.type}' invalid. Allowed: {sorted(VALID_ACTION_TYPES)}",
            )
        if not action.source_citations:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"actions[{i}] must include at least one source_citation",
            )

    now = datetime.utcnow()
    capa_id = f"CAPA-{uuid.uuid4().hex[:8].upper()}"
    actions_payload = [action.model_dump() for action in body.actions]

    capa = CAPA(
        capa_id=capa_id,
        case_id=body.case_id,
        actions=actions_payload,
        status="open",
        effectiveness_result=None,
        effectiveness_reviewed_at=None,
        effectiveness_reviewed_by=None,
        created_at=now,
        updated_at=now,
    )
    db.add(capa)
    db.commit()
    db.refresh(capa)

    audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=body.case_id,
            actor=current_user.user_id,
            action="capa_created",
            previous_value=None,
            new_value=capa_id,
            override_reason=None,
        ),
    )

    return CAPACreateResponse(
        capa_id=capa.capa_id,
        case_id=capa.case_id,
        actions=capa.actions,
        status=capa.status,
        created_at=capa.created_at,
        created_by=current_user.user_id,
    )


@router.put("/{capa_id}/effectiveness", response_model=EffectivenessResponse)
def record_effectiveness(
    capa_id: str,
    body: EffectivenessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.result not in VALID_EFFECTIVENESS_RESULTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid result '{body.result}'. Allowed: {sorted(VALID_EFFECTIVENESS_RESULTS)}",
        )

    capa = db.query(CAPA).filter(CAPA.capa_id == capa_id).first()
    if capa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"CAPA '{capa_id}' not found")

    if capa.effectiveness_result is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"CAPA '{capa_id}' already has an effectiveness review (result: '{capa.effectiveness_result}')",
        )

    if capa.status == "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"CAPA '{capa_id}' is still open. Complete all actions before effectiveness review.",
        )

    case = db.query(Case).filter(Case.case_id == capa.case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{capa.case_id}' not found")

    now = datetime.utcnow()
    previous_case_status = case.status

    capa.effectiveness_result = body.result
    capa.effectiveness_reviewed_at = now
    capa.effectiveness_reviewed_by = current_user.user_id
    capa.status = "effectiveness_reviewed"
    capa.updated_at = now

    if body.result == "pass":
        case.status = "closed"
        case.updated_at = now

    db.commit()
    db.refresh(capa)
    db.refresh(case)

    audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=capa.case_id,
            actor=current_user.user_id,
            action="capa_effectiveness_reviewed",
            previous_value=previous_case_status,
            new_value=case.status,
            override_reason=body.reviewer_notes,
        ),
    )

    return EffectivenessResponse(
        capa_id=capa.capa_id,
        case_id=capa.case_id,
        effectiveness_result=capa.effectiveness_result,
        reviewed_at=now,
        reviewed_by=current_user.user_id,
        case_status=case.status,
    )
