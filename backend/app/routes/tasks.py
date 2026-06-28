from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.audit_event import AuditEventCreate
from app.models.case import Case
from app.models.tasks import Task
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/tasks", tags=["tasks"])
security = HTTPBearer()

# All 4 risk levels — Golden Rule
SLA_HOURS = {"critical": 4, "high": 24, "medium": 72, "low": 168}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
VALID_TASK_TYPES = {"missing_info", "risk_review", "capa_approval", "critical_escalation", "final_closure"}
VALID_DECISIONS = {"approve", "override", "reject"}


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


class TaskCreateRequest(BaseModel):
    case_id: str
    task_type: str
    risk_level: str
    notes: Optional[str] = None


class TaskCreateResponse(BaseModel):
    task_id: str
    case_id: str
    task_type: str
    assigned_to: Optional[str]
    risk_level: str
    sla_deadline: datetime
    status: str
    created_at: datetime


class TaskCompleteRequest(BaseModel):
    decision: str
    override_reason: Optional[str] = None


class TaskCompleteResponse(BaseModel):
    task_id: str
    case_id: str
    decision: str
    override_reason: Optional[str]
    completed_at: datetime
    completed_by: str
    case_status: str


@router.post("", response_model=TaskCreateResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.risk_level not in VALID_RISK_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid risk_level '{body.risk_level}'. Allowed: {sorted(VALID_RISK_LEVELS)}",
        )
    if body.task_type not in VALID_TASK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid task_type '{body.task_type}'. Allowed: {sorted(VALID_TASK_TYPES)}",
        )

    case = db.query(Case).filter(Case.case_id == body.case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{body.case_id}' not found")

    now = datetime.utcnow()
    sla_deadline = now + timedelta(hours=SLA_HOURS[body.risk_level])
    task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"

    # Map to actual Task model columns
    task = Task(
        task_id=task_id,
        case_id=body.case_id,
        task_type=body.task_type,
        jurisdiction=case.jurisdiction,
        risk_level=body.risk_level,
        assigned_to="quality_lead",
        due_at=sla_deadline,
        status="open",
        override_reason=None,
        completed_at=None,
    )
    db.add(task)

    if case.status == "open":
        case.status = "pending_review"
        case.updated_at = now

    db.commit()
    db.refresh(task)

    audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=body.case_id,
            actor=current_user.user_id,
            action="task_created",
            previous_value=None,
            new_value=task_id,
            override_reason=None,
        ),
    )

    return TaskCreateResponse(
        task_id=task.task_id,
        case_id=task.case_id,
        task_type=task.task_type,
        assigned_to=task.assigned_to,
        risk_level=task.risk_level,
        sla_deadline=task.due_at,
        status=task.status,
        created_at=now,
    )


@router.put("/{task_id}/complete", response_model=TaskCompleteResponse)
def complete_task(
    task_id: str,
    body: TaskCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.decision not in VALID_DECISIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid decision '{body.decision}'. Allowed: {sorted(VALID_DECISIONS)}",
        )

    # override_reason required when decision is override — Golden Rule
    if body.decision == "override":
        if not body.override_reason or not body.override_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="override_reason is required when decision is 'override'",
            )

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    if task.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task '{task_id}' is already '{task.status}'",
        )

    case = db.query(Case).filter(Case.case_id == task.case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{task.case_id}' not found")

    now = datetime.utcnow()
    previous_case_status = case.status

    # Store decision in status field + override_reason
    task.status = f"completed_{body.decision}"
    task.override_reason = body.override_reason if body.decision == "override" else None
    task.completed_at = now

    # Trigger case status update
    if body.decision in {"approve", "override"}:
        if case.status == "pending_review":
            case.status = "open"
            case.updated_at = now
    elif body.decision == "reject":
        if case.status != "pending_review":
            case.status = "pending_review"
            case.updated_at = now

    db.commit()
    db.refresh(task)
    db.refresh(case)

    audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=task.case_id,
            actor=current_user.user_id,
            action="task_completed",
            previous_value=previous_case_status,
            new_value=case.status,
            override_reason=task.override_reason,
        ),
    )

    return TaskCompleteResponse(
        task_id=task.task_id,
        case_id=task.case_id,
        decision=body.decision,
        override_reason=task.override_reason,
        completed_at=now,
        completed_by=current_user.user_id,
        case_status=case.status,
    )
