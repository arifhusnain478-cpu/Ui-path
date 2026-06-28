import json
from datetime import datetime, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents import intake_agent
from app.config import settings
from app.database import get_db
from app.models.case import Case
from app.models.complaint import Complaint
from app.services import audit_service

router = APIRouter(prefix="/complaints")
bearer_scheme = HTTPBearer()

# SLA hours — all 4 risk levels (Golden Rule)
SLA_HOURS = {"critical": 4, "high": 24, "medium": 72, "low": 168}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ComplaintRequest(BaseModel):
    product_name: str
    batch_number: Optional[str] = None
    market_code: Literal["US", "EU"]
    complaint_type: Literal["contamination", "labeling", "quality"]
    patient_impact: bool
    description: str


class ComplaintCreateResponse(BaseModel):
    case_id: str
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"]
    jurisdiction: Literal["US", "EU"]
    confidence_score: float
    created_at: datetime


class CaseSummary(BaseModel):
    case_id: str
    product_name: str
    complaint_type: Optional[str] = None
    risk_level: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "pending_review", "closed"]
    jurisdiction: Literal["US", "EU"]
    created_at: datetime


def _next_case_id(db: Session) -> str:
    count = db.query(Case).count()
    return f"C-{(count + 1):03d}"


def _pick_approved_root_cause(investigation_result: dict) -> Optional[str]:
    """
    Auto-selects the highest-likelihood hypothesis from the investigation
    output as the approved root cause for CAPA generation.
    Priority order: high > medium > low.
    Returns None if no hypotheses exist.
    """
    hypotheses = investigation_result.get("root_cause_hypotheses", [])
    if not hypotheses:
        return None

    priority = {"high": 0, "medium": 1, "low": 2}
    sorted_hyps = sorted(
        hypotheses,
        key=lambda h: priority.get(h.get("likelihood", "low"), 2)
    )
    return sorted_hyps[0].get("hypothesis") if sorted_hyps else None


@router.post("", response_model=ComplaintCreateResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    body: ComplaintRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    jurisdiction = body.market_code
    case_id = _next_case_id(db)
    now = datetime.utcnow()

    complaint_record = {
        "case_id": case_id,
        "product_name": body.product_name,
        "batch_number": body.batch_number,
        "jurisdiction": jurisdiction,
        "complaint_type": body.complaint_type,
        "patient_impact": body.patient_impact,
        "description": body.description,
    }

    agent_result = intake_agent.run_intake(complaint_record)
    risk_level: str = agent_result.get("risk_level", "low")
    confidence_score: float = agent_result.get("confidence_score", 0.0)

    # --- RAG + Investigation ---
    rag_context = {}
    investigation_result = {}
    try:
        from app.rag import retriever
        from app.agents import investigation_agent
        rag_context = retriever.retrieve(complaint_record)
        investigation_result = investigation_agent.investigate(complaint_record, rag_context)
    except Exception as e:
        print(f"Investigation error: {e}")

    source_list = rag_context.get("source_list", []) or investigation_result.get("source_list", [])

    # --- CAPA generation ---
    # Auto-pick highest likelihood hypothesis as approved root cause
    capa_plan = []
    try:
        from app.agents import capa_agent
        approved_root_cause = _pick_approved_root_cause(investigation_result)
        if approved_root_cause and investigation_result:
            capa_plan = capa_agent.generate_capa(
                approved_root_cause=approved_root_cause,
                investigation_output=investigation_result,
                jurisdiction=jurisdiction,
                context=rag_context if rag_context else None,
            )
            print(f"CAPA plan generated: {len(capa_plan)} action(s)")
        else:
            print("CAPA skipped: no root cause hypotheses available from investigation")
    except Exception as e:
        print(f"CAPA generation error (non-fatal): {e}")
        capa_plan = []

    # Attach capa_plan to investigation_result so it's stored together
    if investigation_result:
        investigation_result["capa_plan"] = capa_plan
    else:
        investigation_result = {"capa_plan": capa_plan}

    status_value = (
        "pending_review"
        if not body.batch_number
        else "open"
    )

    # Calculate SLA deadline based on risk_level
    sla_deadline = now + timedelta(hours=SLA_HOURS.get(risk_level, 72))

    db_complaint = Complaint(
        case_id=case_id,
        jurisdiction=jurisdiction,
        risk_level=risk_level,
        confidence_score=confidence_score,
        status=status_value,
        product_name=body.product_name,
        batch_number=body.batch_number,
        complaint_type=body.complaint_type,
        source_list=source_list,
        override_reason=None,
    )
    db.add(db_complaint)

    db_case = Case(
        case_id=case_id,
        jurisdiction=jurisdiction,
        risk_level=risk_level,
        status=status_value,
        assigned_to=None,
        current_stage="Stage2_Investigation",
        created_at=now,
        updated_at=now,
        override_reason=None,
        investigation_output=json.dumps(investigation_result) if investigation_result else None,
        sla_deadline=sla_deadline,
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    from app.models.audit_event import AuditEventCreate
    audit_service.create_audit_event(
        db=db,
        event=AuditEventCreate(
            case_id=case_id,
            actor=current_user["user_id"],
            action="complaint_created",
            previous_value=None,
            new_value=status_value,
            override_reason=None,
        ),
    )

    return ComplaintCreateResponse(
        case_id=case_id,
        risk_level=risk_level,
        status=status_value,
        jurisdiction=jurisdiction,
        confidence_score=confidence_score,
        created_at=now,
    )


@router.get("", response_model=List[CaseSummary])
def list_complaints(
    jurisdiction: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Case, Complaint).join(Complaint, Case.case_id == Complaint.case_id)

    if jurisdiction:
        query = query.filter(Case.jurisdiction == jurisdiction)
    if status:
        query = query.filter(Case.status == status)
    if risk_level:
        query = query.filter(Case.risk_level == risk_level)

    rows = query.all()
    return [
        CaseSummary(
            case_id=case.case_id,
            product_name=complaint.product_name,
            complaint_type=complaint.complaint_type,
            risk_level=case.risk_level,
            status=case.status,
            jurisdiction=case.jurisdiction,
            created_at=case.created_at,
        )
        for case, complaint in rows
    ]


@router.get("/{case_id}")
def get_complaint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found.",
        )
    complaint = db.query(Complaint).filter(Complaint.case_id == case_id).first()

    investigation_output = {}
    if case.investigation_output:
        try:
            investigation_output = json.loads(case.investigation_output)
        except Exception:
            investigation_output = {}

    return {
        "case_id": case.case_id,
        "jurisdiction": case.jurisdiction,
        "risk_level": case.risk_level,
        "status": case.status,
        "current_stage": case.current_stage,
        "assigned_to": case.assigned_to,
        "override_reason": case.override_reason,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "product_name": complaint.product_name if complaint else None,
        "batch_number": complaint.batch_number if complaint else None,
        "complaint_type": complaint.complaint_type if complaint else None,
        "confidence_score": complaint.confidence_score if complaint else None,
        "source_list": complaint.source_list if complaint else [],
        "investigation_output": investigation_output,
        "capa_plan": investigation_output.get("capa_plan", []),
        "sla_deadline": case.sla_deadline if hasattr(case, "sla_deadline") else None,
    }
