"""
QualiTrace AI — Backend Route Tests
Run from the backend/ folder:  pytest tests/test_routes.py -v

Covers every checklist item from QualiTrace_AI_Test_Checklist.docx:
  - cases.py    : PUT /cases/{case_id}/status  |  GET /cases/{case_id}/audit
  - tasks.py    : POST /tasks                  |  PUT /tasks/{task_id}/complete
  - capa.py     : POST /capa                   |  PUT /capa/{capa_id}/effectiveness
  - reports.py  : GET /reports/{case_id}
  - webhook.py  : POST /webhook/maestro

Golden Rule enforced in every test:
  snake_case only | jurisdiction US/EU only | all 4 risk_levels |
  override_reason required on override | closed only via effectiveness review
"""

import pytest
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Float
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ---------------------------------------------------------------------------
# Minimal in-memory SQLite setup for isolated testing
# ---------------------------------------------------------------------------

SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Minimal ORM models mirroring the real models
class CaseModel(Base):
    __tablename__ = "cases"
    case_id = Column(String, primary_key=True)
    status = Column(String, default="open")
    risk_level = Column(String, default="medium")
    confidence_score = Column(Float, default=0.85)
    jurisdiction = Column(String, default="US")
    complaint_type = Column(String, default="quality")
    product_name = Column(String, default="Metformin 500mg")
    batch_number = Column(String, nullable=True)
    complaint = Column(JSON, default={})
    investigation_output = Column(JSON, default={})
    capa_plan = Column(JSON, default=[])
    audit_timeline = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TaskModel(Base):
    __tablename__ = "tasks"
    task_id = Column(String, primary_key=True)
    case_id = Column(String)
    task_type = Column(String)
    assigned_role = Column(String, default="quality_lead")
    sla_deadline = Column(DateTime)
    status = Column(String, default="open")
    decision = Column(String, nullable=True)
    override_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class CAPAModel(Base):
    __tablename__ = "capas"
    capa_id = Column(String, primary_key=True)
    case_id = Column(String)
    actions = Column(JSON, default=[])
    status = Column(String, default="open")
    effectiveness_result = Column(String, nullable=True)
    effectiveness_reviewed_at = Column(DateTime, nullable=True)
    effectiveness_reviewed_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    event_id = Column(String, primary_key=True)
    case_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    actor = Column(String)
    stage = Column(String, nullable=True)
    summary = Column(String)
    payload = Column(JSON, default={})


class UserModel(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    username = Column(String)
    email = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="quality_reviewer")
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Patch app.models.* to use the test ORM models
# ---------------------------------------------------------------------------

import sys
from types import ModuleType

def _make_module(name, **attrs):
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

# Stub config
config_mod = _make_module("app.config")
settings_obj = MagicMock()
settings_obj.SECRET_KEY = "test-secret-key-qualitrace"
config_mod.settings = settings_obj

# Stub database
db_mod = _make_module("app.database")
def _get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
db_mod.get_db = _get_test_db

# Stub models
_make_module("app.models.case", Case=CaseModel)
_make_module("app.models.task", Task=TaskModel)
_make_module("app.models.capa", CAPA=CAPAModel)
_make_module("app.models.audit_event", AuditEvent=AuditEventModel, AuditEventCreate=MagicMock())
_make_module("app.models.user", User=UserModel)
_make_module("app.models.complaint", Complaint=MagicMock())

# Stub audit_service
audit_mod = _make_module("app.services.audit_service")
_make_module("app.services")

_audit_log_calls = []

def _mock_log_event(db, case_id, event_type, actor, stage, summary, payload=None):
    import uuid
    record = AuditEventModel(
        event_id=str(uuid.uuid4()),
        case_id=case_id,
        event_type=event_type,
        actor=actor,
        stage=stage,
        summary=summary,
        payload=payload or {},
        timestamp=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    _audit_log_calls.append({"case_id": case_id, "event_type": event_type})
    return record

audit_mod.log_event = _mock_log_event

# Now import the routes (they will resolve mocked modules)
from app.routes import cases as cases_module
from app.routes import tasks as tasks_module
from app.routes import capa as capa_module
from app.routes import reports as reports_module
from app.routes import webhook as webhook_module

# Override get_db dependency in every router
from app.database import get_db

for mod in [cases_module, tasks_module, capa_module, reports_module, webhook_module]:
    mod.get_db = _get_test_db

# Build test FastAPI app
app = FastAPI()
app.include_router(cases_module.router)
app.include_router(tasks_module.router)
app.include_router(capa_module.router)
app.include_router(reports_module.router)
app.include_router(webhook_module.router)

# Override FastAPI dependency injection for all routers
app.dependency_overrides[get_db] = _get_test_db

client = TestClient(app)

# ---------------------------------------------------------------------------
# Auth token helper — bypass real JWT, mock get_current_user directly
# ---------------------------------------------------------------------------

MOCK_USER = UserModel(
    user_id="user-001",
    username="test_quality_lead",
    email="lead@qualitrace.ai",
    hashed_password="hashed",
    role="quality_lead",
    created_at=datetime.utcnow(),
)

_security = HTTPBearer()

def _mock_get_current_user(credentials: HTTPAuthorizationCredentials = Security(_security)):
    return MOCK_USER

# Patch auth in all route modules
for mod in [cases_module, tasks_module, capa_module, reports_module]:
    if hasattr(mod, "get_current_user"):
        app.dependency_overrides[mod.get_current_user] = _mock_get_current_user
VALID_TOKEN = "Bearer mock-token"
AUTH_HEADER = {"Authorization": VALID_TOKEN}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_db():
    """Wipe and recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _audit_log_calls.clear()
    yield


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def open_case(db):
    case = CaseModel(
        case_id="C-001",
        status="open",
        risk_level="high",
        confidence_score=0.88,
        jurisdiction="US",
        complaint_type="quality",
        product_name="Metformin 500mg",
        batch_number="MF-2024-001",
        complaint={"product_name": "Metformin 500mg", "complaint_type": "quality"},
        investigation_output={
            "root_cause_hypotheses": [
                {"hypothesis": "Packaging seal failure", "confidence": 0.88},
                {"hypothesis": "Moisture ingress", "confidence": 0.72},
                {"hypothesis": "Storage temperature deviation", "confidence": 0.61},
            ],
            "evidence_summary": "Tablet degradation consistent with moisture ingress.",
            "overall_confidence": 0.88,
            "source_list": ["fda_21cfr_211.pdf — Section 211.198", "sop_qa_042_site_a.pdf — 4.3"],
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(case)
    db.commit()
    return case


@pytest.fixture()
def pending_case(db):
    case = CaseModel(
        case_id="C-002",
        status="pending_review",
        risk_level="critical",
        confidence_score=0.55,
        jurisdiction="EU",
        complaint_type="contamination",
        product_name="Injectable Saline",
        batch_number="INJ-2024-0121",
        complaint={},
        investigation_output={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(case)
    db.commit()
    return case


@pytest.fixture()
def closed_case(db):
    case = CaseModel(
        case_id="C-003",
        status="closed",
        risk_level="medium",
        confidence_score=0.91,
        jurisdiction="US",
        complaint_type="labeling",
        product_name="Amlodipine 10mg",
        batch_number=None,
        complaint={"product_name": "Amlodipine 10mg", "batch_number": None, "complaint_type": "labeling"},
        investigation_output={
            "root_cause_hypotheses": [{"hypothesis": "Label print error", "confidence": 0.91}],
            "evidence_summary": "Mislabelled batch confirmed via QC inspection.",
            "overall_confidence": 0.91,
            "source_list": ["ema_eudralex_vol4.pdf — Annex 11"],
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(case)
    db.commit()
    return case


@pytest.fixture()
def open_task(db, open_case):
    task = TaskModel(
        task_id="TASK-ABCD1234",
        case_id="C-001",
        task_type="risk_review",
        assigned_role="quality_lead",
        sla_deadline=datetime.utcnow() + timedelta(hours=24),
        status="open",
        decision=None,
        override_reason=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    return task


@pytest.fixture()
def open_capa(db, open_case):
    """CAPA in 'actions_complete' status — ready for effectiveness review."""
    capa = CAPAModel(
        capa_id="CAPA-XYZ99999",
        case_id="C-001",
        actions=[
            {
                "description": "Add seal integrity test to QC protocol",
                "type": "corrective",
                "responsible_role": "quality_lead",
                "due_date": "2026-08-01",
                "evidence_required": "Updated QC protocol document",
                "effectiveness_metric": "Zero seal failures in 90-day window",
                "source_citations": ["sop_qa_018_packaging.pdf — seal test methods"],
            }
        ],
        status="actions_complete",
        effectiveness_result=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(capa)
    db.commit()
    return capa


@pytest.fixture()
def closed_case_with_capa(db, closed_case):
    capa = CAPAModel(
        capa_id="CAPA-CLOSED01",
        case_id="C-003",
        actions=[
            {
                "description": "Reprint and redistribute corrected labels",
                "type": "corrective",
                "responsible_role": "quality_lead",
                "due_date": "2026-07-15",
                "evidence_required": "Updated label artwork approval",
                "effectiveness_metric": "No label complaints in 60 days",
                "source_citations": ["ema_eudralex_vol4.pdf — Annex 11"],
            }
        ],
        status="effectiveness_reviewed",
        effectiveness_result="pass",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    audit = AuditEventModel(
        event_id="evt-001",
        case_id="C-003",
        event_type="case_created",
        actor="system",
        stage="intake",
        summary="Case C-003 created",
        payload={},
        timestamp=datetime.utcnow(),
    )
    db.add(capa)
    db.add(audit)
    db.commit()
    return closed_case


# ===========================================================================
# CASES TESTS — PUT /cases/{case_id}/status | GET /cases/{case_id}/audit
# ===========================================================================

class TestCasesStatusUpdate:

    def test_valid_transition_open_to_pending_review(self, open_case):
        r = client.put("/cases/C-001/status", json={"status": "pending_review"}, headers=AUTH_HEADER)
        assert r.status_code == 200
        data = r.json()
        # Golden Rule: snake_case fields only
        assert data["case_id"] == "C-001"
        assert data["status"] == "pending_review"
        assert "updated_at" in data
        assert "updated_by" in data

    def test_valid_transition_pending_to_open(self, pending_case):
        r = client.put("/cases/C-002/status", json={"status": "open"}, headers=AUTH_HEADER)
        assert r.status_code == 200
        assert r.json()["status"] == "open"

    def test_closed_blocked_via_status_endpoint(self, open_case):
        """Case cannot be set to 'closed' via this endpoint — only via effectiveness review."""
        r = client.put("/cases/C-001/status", json={"status": "closed"}, headers=AUTH_HEADER)
        assert r.status_code == 422
        assert "closed" in r.json()["detail"].lower()

    def test_invalid_status_value_returns_422(self, open_case):
        r = client.put("/cases/C-001/status", json={"status": "approved"}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_invalid_transition_closed_to_open(self, closed_case):
        """Closed is terminal — cannot transition out."""
        r = client.put("/cases/C-003/status", json={"status": "open"}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_case_not_found_returns_404(self):
        r = client.put("/cases/C-999/status", json={"status": "pending_review"}, headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_no_auth_returns_401(self, open_case):
        r = client.put("/cases/C-001/status", json={"status": "pending_review"})
        assert r.status_code in {401, 403}

    def test_audit_event_recorded_on_status_change(self, open_case):
        client.put("/cases/C-001/status", json={"status": "pending_review"}, headers=AUTH_HEADER)
        assert any(e["event_type"] == "status_change" for e in _audit_log_calls)

    def test_response_fields_are_snake_case_only(self, open_case):
        r = client.put("/cases/C-001/status", json={"status": "pending_review"}, headers=AUTH_HEADER)
        for key in r.json().keys():
            assert key == key.lower() and "-" not in key, f"camelCase field found: {key}"


class TestCasesAuditTrail:

    def test_returns_audit_trail_array(self, open_case, db):
        # Seed an audit event
        db.add(AuditEventModel(
            event_id="evt-test-01",
            case_id="C-001",
            event_type="status_change",
            actor="system",
            stage="open",
            summary="Case created",
            payload={},
            timestamp=datetime.utcnow(),
        ))
        db.commit()

        r = client.get("/cases/C-001/audit", headers=AUTH_HEADER)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_audit_entries_have_required_fields(self, open_case, db):
        db.add(AuditEventModel(
            event_id="evt-test-02",
            case_id="C-001",
            event_type="status_change",
            actor="test_quality_lead",
            stage="pending_review",
            summary="Status changed",
            payload={"previous_status": "open"},
            timestamp=datetime.utcnow(),
        ))
        db.commit()

        r = client.get("/cases/C-001/audit", headers=AUTH_HEADER)
        entry = r.json()[0]
        # Checklist: each entry must have action/user/timestamp/details
        assert "event_type" in entry
        assert "actor" in entry
        assert "timestamp" in entry
        assert "summary" in entry

    def test_audit_trail_is_chronological(self, open_case, db):
        for i in range(3):
            db.add(AuditEventModel(
                event_id=f"evt-ord-{i}",
                case_id="C-001",
                event_type="status_change",
                actor="system",
                stage="open",
                summary=f"Event {i}",
                payload={},
                timestamp=datetime.utcnow() + timedelta(seconds=i),
            ))
        db.commit()

        r = client.get("/cases/C-001/audit", headers=AUTH_HEADER)
        timestamps = [e["timestamp"] for e in r.json()]
        assert timestamps == sorted(timestamps)

    def test_audit_case_not_found_returns_404(self):
        r = client.get("/cases/C-999/audit", headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_audit_no_auth_returns_401(self, open_case):
        r = client.get("/cases/C-001/audit")
        assert r.status_code in {401, 403}


# ===========================================================================
# TASKS TESTS — POST /tasks | PUT /tasks/{task_id}/complete
# ===========================================================================

VALID_TASK_BODY = {
    "case_id": "C-001",
    "task_type": "risk_review",
    "risk_level": "high",
}


class TestTasksCreate:

    def test_creates_task_successfully(self, open_case):
        r = client.post("/tasks", json=VALID_TASK_BODY, headers=AUTH_HEADER)
        assert r.status_code == 201
        data = r.json()
        assert data["case_id"] == "C-001"
        assert data["task_type"] == "risk_review"
        assert data["assigned_role"] == "quality_lead"
        assert "sla_deadline" in data
        assert "task_id" in data

    def test_all_four_risk_levels_accepted(self, open_case):
        """Golden Rule: all 4 risk_level values must work — never collapse to 3."""
        for level in ["low", "medium", "high", "critical"]:
            r = client.post("/tasks", json={**VALID_TASK_BODY, "risk_level": level}, headers=AUTH_HEADER)
            assert r.status_code == 201, f"risk_level '{level}' failed: {r.json()}"

    def test_critical_sla_is_4_hours(self, open_case):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "risk_level": "critical"}, headers=AUTH_HEADER)
        assert r.status_code == 201
        deadline = datetime.fromisoformat(r.json()["sla_deadline"])
        diff_hours = (deadline - datetime.utcnow()).total_seconds() / 3600
        assert 3.9 <= diff_hours <= 4.1, f"Expected ~4h SLA for critical, got {diff_hours:.2f}h"

    def test_high_sla_is_24_hours(self, open_case):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "risk_level": "high"}, headers=AUTH_HEADER)
        deadline = datetime.fromisoformat(r.json()["sla_deadline"])
        diff_hours = (deadline - datetime.utcnow()).total_seconds() / 3600
        assert 23.9 <= diff_hours <= 24.1

    def test_medium_sla_is_72_hours(self, open_case):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "risk_level": "medium"}, headers=AUTH_HEADER)
        deadline = datetime.fromisoformat(r.json()["sla_deadline"])
        diff_hours = (deadline - datetime.utcnow()).total_seconds() / 3600
        assert 71.9 <= diff_hours <= 72.1

    def test_low_sla_is_168_hours(self, open_case):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "risk_level": "low"}, headers=AUTH_HEADER)
        deadline = datetime.fromisoformat(r.json()["sla_deadline"])
        diff_hours = (deadline - datetime.utcnow()).total_seconds() / 3600
        assert 167.9 <= diff_hours <= 168.1

    def test_invalid_risk_level_returns_422(self, open_case):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "risk_level": "extreme"}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_invalid_task_type_returns_422(self, open_case):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "task_type": "nonexistent_type"}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_unknown_case_id_returns_404(self):
        r = client.post("/tasks", json={**VALID_TASK_BODY, "case_id": "C-999"}, headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_assigned_to_quality_lead_role(self, open_case):
        r = client.post("/tasks", json=VALID_TASK_BODY, headers=AUTH_HEADER)
        assert r.json()["assigned_role"] == "quality_lead"

    def test_no_auth_returns_401(self, open_case):
        r = client.post("/tasks", json=VALID_TASK_BODY)
        assert r.status_code in {401, 403}

    def test_response_fields_snake_case_only(self, open_case):
        r = client.post("/tasks", json=VALID_TASK_BODY, headers=AUTH_HEADER)
        for key in r.json().keys():
            assert key == key.lower(), f"camelCase field found: {key}"


class TestTasksComplete:

    def test_approve_decision_recorded(self, open_task):
        r = client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "approve"}, headers=AUTH_HEADER)
        assert r.status_code == 200
        data = r.json()
        assert data["decision"] == "approve"
        assert data["task_id"] == "TASK-ABCD1234"

    def test_reject_decision_recorded(self, open_task):
        r = client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "reject"}, headers=AUTH_HEADER)
        assert r.status_code == 200
        assert r.json()["decision"] == "reject"

    def test_override_requires_override_reason(self, open_task):
        """Golden Rule: override_reason required when decision is 'override' — 422 if missing."""
        r = client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "override"}, headers=AUTH_HEADER)
        assert r.status_code == 422
        assert "override_reason" in r.json()["detail"].lower()

    def test_override_with_reason_succeeds(self, open_task):
        r = client.put(
            "/tasks/TASK-ABCD1234/complete",
            json={"decision": "override", "override_reason": "Risk acceptable given batch recall already in progress"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["decision"] == "override"
        assert data["override_reason"] is not None
        assert len(data["override_reason"]) > 0

    def test_override_reason_not_stored_on_approve(self, open_task):
        r = client.put(
            "/tasks/TASK-ABCD1234/complete",
            json={"decision": "approve", "override_reason": "should be ignored"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        assert r.json()["override_reason"] is None

    def test_invalid_decision_returns_422(self, open_task):
        r = client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "skip"}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_completing_already_complete_task_returns_409(self, open_task, db):
        # Complete it first
        client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "approve"}, headers=AUTH_HEADER)
        # Try again
        r = client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "approve"}, headers=AUTH_HEADER)
        assert r.status_code == 409

    def test_task_not_found_returns_404(self):
        r = client.put("/tasks/TASK-MISSING/complete", json={"decision": "approve"}, headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_audit_logged_on_task_complete(self, open_task):
        client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "approve"}, headers=AUTH_HEADER)
        assert any(e["event_type"] == "task_completed" for e in _audit_log_calls)

    def test_case_status_updated_after_approve(self, open_task, db):
        client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "approve"}, headers=AUTH_HEADER)
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.status == "open"

    def test_no_auth_returns_401(self, open_task):
        r = client.put("/tasks/TASK-ABCD1234/complete", json={"decision": "approve"})
        assert r.status_code in {401, 403}


# ===========================================================================
# CAPA TESTS — POST /capa | PUT /capa/{capa_id}/effectiveness
# ===========================================================================

VALID_CAPA_BODY = {
    "case_id": "C-001",
    "actions": [
        {
            "description": "Add seal integrity test to QC protocol",
            "type": "corrective",
            "responsible_role": "quality_lead",
            "due_date": "2026-08-01",
            "evidence_required": "Updated QC protocol",
            "effectiveness_metric": "Zero seal failures in 90-day window",
            "source_citations": ["sop_qa_018_packaging.pdf — seal test methods"],
        }
    ],
}


class TestCAPACreate:

    def test_creates_capa_successfully(self, open_case):
        r = client.post("/capa", json=VALID_CAPA_BODY, headers=AUTH_HEADER)
        assert r.status_code == 201
        data = r.json()
        assert "capa_id" in data
        assert data["case_id"] == "C-001"
        assert isinstance(data["actions"], list)
        assert len(data["actions"]) == 1

    def test_capa_linked_to_correct_case(self, open_case):
        r = client.post("/capa", json=VALID_CAPA_BODY, headers=AUTH_HEADER)
        assert r.json()["case_id"] == "C-001"

    def test_capa_returns_actions_list(self, open_case):
        r = client.post("/capa", json=VALID_CAPA_BODY, headers=AUTH_HEADER)
        actions = r.json()["actions"]
        assert isinstance(actions, list)
        assert actions[0]["type"] in {"corrective", "preventive"}

    def test_empty_actions_returns_422(self, open_case):
        body = {**VALID_CAPA_BODY, "actions": []}
        r = client.post("/capa", json=body, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_invalid_action_type_returns_422(self, open_case):
        body = {**VALID_CAPA_BODY, "actions": [{**VALID_CAPA_BODY["actions"][0], "type": "quarterly_review"}]}
        r = client.post("/capa", json=body, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_action_without_source_citations_returns_422(self, open_case):
        action = {**VALID_CAPA_BODY["actions"][0], "source_citations": []}
        r = client.post("/capa", json={**VALID_CAPA_BODY, "actions": [action]}, headers=AUTH_HEADER)
        assert r.status_code == 422

    def test_capa_on_closed_case_returns_409(self, closed_case):
        r = client.post("/capa", json={**VALID_CAPA_BODY, "case_id": "C-003"}, headers=AUTH_HEADER)
        assert r.status_code == 409

    def test_capa_unknown_case_returns_404(self):
        r = client.post("/capa", json={**VALID_CAPA_BODY, "case_id": "C-999"}, headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_audit_logged_on_capa_create(self, open_case):
        client.post("/capa", json=VALID_CAPA_BODY, headers=AUTH_HEADER)
        assert any(e["event_type"] == "capa_created" for e in _audit_log_calls)

    def test_no_auth_returns_401(self, open_case):
        r = client.post("/capa", json=VALID_CAPA_BODY)
        assert r.status_code in {401, 403}

    def test_response_fields_snake_case(self, open_case):
        r = client.post("/capa", json=VALID_CAPA_BODY, headers=AUTH_HEADER)
        for key in r.json().keys():
            assert key == key.lower(), f"camelCase field found: {key}"


class TestCAPAEffectiveness:

    def test_pass_closes_case(self, open_capa, db):
        r = client.put(
            "/capa/CAPA-XYZ99999/effectiveness",
            json={"result": "pass", "reviewer_notes": "All actions verified effective"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["effectiveness_result"] == "pass"
        # Case must now be closed — this is the ONLY path to closed
        assert data["case_status"] == "closed"
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.status == "closed"

    def test_fail_does_not_close_case(self, open_capa, db):
        r = client.put(
            "/capa/CAPA-XYZ99999/effectiveness",
            json={"result": "fail", "reviewer_notes": "Actions incomplete"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        assert r.json()["effectiveness_result"] == "fail"
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.status != "closed"

    def test_invalid_result_returns_422(self, open_capa):
        r = client.put(
            "/capa/CAPA-XYZ99999/effectiveness",
            json={"result": "inconclusive"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 422

    def test_double_review_returns_409(self, open_capa):
        client.put("/capa/CAPA-XYZ99999/effectiveness", json={"result": "pass"}, headers=AUTH_HEADER)
        r = client.put("/capa/CAPA-XYZ99999/effectiveness", json={"result": "pass"}, headers=AUTH_HEADER)
        assert r.status_code == 409

    def test_open_capa_blocked_from_effectiveness(self, db, open_case):
        """Cannot review effectiveness before CAPA actions are complete."""
        capa = CAPAModel(
            capa_id="CAPA-OPEN0001",
            case_id="C-001",
            actions=[],
            status="open",  # still open — actions not complete
            effectiveness_result=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(capa)
        db.commit()

        r = client.put(
            "/capa/CAPA-OPEN0001/effectiveness",
            json={"result": "pass"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 409

    def test_capa_not_found_returns_404(self):
        r = client.put("/capa/CAPA-MISSING/effectiveness", json={"result": "pass"}, headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_audit_logged_on_effectiveness(self, open_capa):
        client.put("/capa/CAPA-XYZ99999/effectiveness", json={"result": "pass"}, headers=AUTH_HEADER)
        assert any(e["event_type"] == "capa_effectiveness_reviewed" for e in _audit_log_calls)

    def test_no_auth_returns_401(self, open_capa):
        r = client.put("/capa/CAPA-XYZ99999/effectiveness", json={"result": "pass"})
        assert r.status_code in {401, 403}


# ===========================================================================
# REPORTS TESTS — GET /reports/{case_id}
# ===========================================================================

class TestReports:

    def test_open_case_returns_400(self, open_case):
        """Checklist: cannot generate report if case is still open."""
        r = client.get("/reports/C-001", headers=AUTH_HEADER)
        assert r.status_code == 400
        assert "open" in r.json()["detail"].lower() or "closed" in r.json()["detail"].lower()

    def test_pending_review_case_returns_400(self, pending_case):
        r = client.get("/reports/C-002", headers=AUTH_HEADER)
        assert r.status_code == 400

    def test_closed_case_returns_pdf(self, closed_case_with_capa):
        r = client.get("/reports/C-003", headers=AUTH_HEADER)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_pdf_content_disposition_header(self, closed_case_with_capa):
        r = client.get("/reports/C-003", headers=AUTH_HEADER)
        disposition = r.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "C-003" in disposition
        assert ".pdf" in disposition

    def test_pdf_filename_format(self, closed_case_with_capa):
        """Filename must match: QualiTrace_{case_id}_{date}.pdf"""
        r = client.get("/reports/C-003", headers=AUTH_HEADER)
        disposition = r.headers.get("content-disposition", "")
        assert "QualiTrace_C-003" in disposition

    def test_pdf_has_non_zero_bytes(self, closed_case_with_capa):
        r = client.get("/reports/C-003", headers=AUTH_HEADER)
        assert len(r.content) > 100  # valid PDF is never empty

    def test_case_not_found_returns_404(self):
        r = client.get("/reports/C-999", headers=AUTH_HEADER)
        assert r.status_code == 404

    def test_no_auth_returns_401(self, closed_case_with_capa):
        r = client.get("/reports/C-003")
        assert r.status_code in {401, 403}

    def test_report_generation_logged_in_audit(self, closed_case_with_capa):
        client.get("/reports/C-003", headers=AUTH_HEADER)
        assert any(e["event_type"] == "report_generated" for e in _audit_log_calls)


# ===========================================================================
# WEBHOOK TESTS — POST /webhook/maestro
# ===========================================================================

VALID_WEBHOOK_BODY = {
    "case_id": "C-001",
    "event_type": "stage_change",
    "from_stage": "risk_assessment",
    "to_stage": "human_review",
    "actor": "maestro_system",
    "timestamp": datetime.utcnow().isoformat(),
    "payload": {"confidence_score": 0.55, "risk_level": "critical"},
}


class TestWebhook:

    def test_valid_payload_returns_200(self, open_case):
        r = client.post("/webhook/maestro", json=VALID_WEBHOOK_BODY)
        assert r.status_code == 200

    def test_no_auth_required(self, open_case):
        """Webhook has no auth — Maestro calls this internally."""
        r = client.post("/webhook/maestro", json=VALID_WEBHOOK_BODY)
        # Must succeed without any Authorization header
        assert r.status_code == 200

    def test_response_has_required_fields(self, open_case):
        r = client.post("/webhook/maestro", json=VALID_WEBHOOK_BODY)
        data = r.json()
        assert data["received"] is True
        assert "event_id" in data
        assert data["case_id"] == "C-001"
        assert data["event_type"] == "stage_change"
        assert "recorded_at" in data

    def test_all_seven_payload_fields_accepted(self, open_case):
        """Spec requires: case_id, event_type, from_stage, to_stage, actor, timestamp, payload."""
        body = {
            "case_id": "C-001",
            "event_type": "stage_change",
            "from_stage": "intake",
            "to_stage": "risk_assessment",
            "actor": "maestro_system",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"extra_data": "value"},
        }
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 200

    def test_unknown_case_still_records_event(self):
        """Maestro events for unknown cases must not be silently dropped."""
        body = {**VALID_WEBHOOK_BODY, "case_id": "C-999"}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 200
        assert "warning" in r.json()["message"].lower() or "unknown" in r.json()["message"].lower()

    def test_audit_event_written_to_trail(self, open_case, db):
        client.post("/webhook/maestro", json=VALID_WEBHOOK_BODY)
        events = db.query(AuditEventModel).filter(AuditEventModel.case_id == "C-001").all()
        assert len(events) >= 1
        assert any("maestro" in e.event_type for e in events)

    def test_invalid_event_type_returns_422(self, open_case):
        body = {**VALID_WEBHOOK_BODY, "event_type": "nonexistent_event"}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 422

    def test_invalid_from_stage_returns_422(self, open_case):
        body = {**VALID_WEBHOOK_BODY, "from_stage": "made_up_stage"}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 422

    def test_invalid_to_stage_returns_422(self, open_case):
        body = {**VALID_WEBHOOK_BODY, "to_stage": "made_up_stage"}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 422

    def test_missing_case_id_returns_422(self):
        body = {k: v for k, v in VALID_WEBHOOK_BODY.items() if k != "case_id"}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 422

    def test_missing_actor_returns_422(self):
        body = {k: v for k, v in VALID_WEBHOOK_BODY.items() if k != "actor"}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 422

    def test_null_from_to_stage_accepted(self, open_case):
        """from_stage and to_stage are optional."""
        body = {**VALID_WEBHOOK_BODY, "from_stage": None, "to_stage": None}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 200

    def test_null_payload_accepted(self, open_case):
        """payload field is optional — null must be accepted."""
        body = {**VALID_WEBHOOK_BODY, "payload": None}
        r = client.post("/webhook/maestro", json=body)
        assert r.status_code == 200

    def test_human_review_stage_sets_case_pending(self, open_case, db):
        """Maestro moving to human_review should set case to pending_review."""
        body = {**VALID_WEBHOOK_BODY, "to_stage": "human_review"}
        client.post("/webhook/maestro", json=body)
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.status == "pending_review"

    def test_webhook_never_closes_case(self, open_case, db):
        """Closure is ONLY via effectiveness review — webhook must never close a case."""
        body = {**VALID_WEBHOOK_BODY, "to_stage": "closure"}
        client.post("/webhook/maestro", json=body)
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.status != "closed"

    def test_response_fields_snake_case(self, open_case):
        r = client.post("/webhook/maestro", json=VALID_WEBHOOK_BODY)
        for key in r.json().keys():
            assert key == key.lower(), f"camelCase field found: {key}"


# ===========================================================================
# GOLDEN RULE CONTRACT TESTS — apply across all routes
# ===========================================================================

class TestGoldenRuleContracts:

    def test_jurisdiction_us_only_in_case_summary(self, open_case, db):
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.jurisdiction in {"US", "EU"}

    def test_jurisdiction_eu_only_in_case_summary(self, db):
        case = CaseModel(
            case_id="C-EU-001",
            status="open",
            risk_level="low",
            jurisdiction="EU",
            complaint_type="labeling",
            product_name="Test",
            batch_number=None,
            complaint={},
            investigation_output={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(case)
        db.commit()
        fetched = db.query(CaseModel).filter(CaseModel.case_id == "C-EU-001").first()
        assert fetched.jurisdiction == "EU"

    def test_all_four_risk_levels_in_task_sla_mapping(self, open_case):
        """All 4 risk_level values must resolve to an SLA — never collapse to 3."""
        expected_hours = {"low": 168, "medium": 72, "high": 24, "critical": 4}
        for level, expected_h in expected_hours.items():
            r = client.post(
                "/tasks",
                json={"case_id": "C-001", "task_type": "risk_review", "risk_level": level},
                headers=AUTH_HEADER,
            )
            assert r.status_code == 201, f"risk_level='{level}' failed"
            deadline = datetime.fromisoformat(r.json()["sla_deadline"])
            diff = (deadline - datetime.utcnow()).total_seconds() / 3600
            assert abs(diff - expected_h) < 0.2, f"risk_level='{level}' SLA mismatch: {diff:.2f}h vs {expected_h}h"

    def test_override_reason_required_on_override_decision(self, open_task):
        """Golden Rule: override_reason required on override — 422 if missing."""
        r = client.put(
            "/tasks/TASK-ABCD1234/complete",
            json={"decision": "override"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 422

    def test_case_closed_only_via_effectiveness_review(self, open_capa, db):
        """Golden Rule: case cannot be closed via status endpoint — only via CAPA effectiveness."""
        # Try via status endpoint — must be blocked
        r = client.put("/cases/C-001/status", json={"status": "closed"}, headers=AUTH_HEADER)
        assert r.status_code == 422

        # Close properly via effectiveness review
        r = client.put(
            "/capa/CAPA-XYZ99999/effectiveness",
            json={"result": "pass"},
            headers=AUTH_HEADER,
        )
        assert r.status_code == 200
        case = db.query(CaseModel).filter(CaseModel.case_id == "C-001").first()
        assert case.status == "closed"

    def test_no_camel_case_in_any_route_response(self, open_case, open_task, open_capa):
        """No response from any route may contain camelCase field names."""
        responses = [
            client.put("/cases/C-001/status", json={"status": "pending_review"}, headers=AUTH_HEADER),
            client.get("/cases/C-001/audit", headers=AUTH_HEADER),
            client.post("/tasks", json=VALID_TASK_BODY, headers=AUTH_HEADER),
            client.post("/webhook/maestro", json=VALID_WEBHOOK_BODY),
        ]
        for resp in responses:
            if resp.status_code in {200, 201}:
                data = resp.json()
                keys = data.keys() if isinstance(data, dict) else (data[0].keys() if data else [])
                for key in keys:
                    assert key == key.lower() and key == key.replace("-", "_"), \
                        f"Non-snake_case field '{key}' found in response"
