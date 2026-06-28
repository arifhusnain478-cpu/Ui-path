import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.audit_event import AuditEvent
from app.models.capa import CAPA
from app.models.case import Case
from app.models.user import User
from app.services import audit_service

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

router = APIRouter(prefix="/reports", tags=["reports"])
security = HTTPBearer()

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

def _build_pdf(case: Case, capa_records: List[Any], audit_events: List[Any]) -> bytes:
    """Build the case closure PDF report using reportlab and return raw bytes."""

    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6,
        textColor=colors.HexColor("#1a1a2e"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=4,
        textColor=colors.HexColor("#16213e"),
    )
    body_style = styles["BodyText"]
    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=8,
        textColor=colors.HexColor("#555555"),
    )

    story = []

    # ---- Title block ----
    story.append(Paragraph("QualiTrace AI", title_style))
    story.append(Paragraph(f"Case Closure Report — {case.case_id}", styles["Heading1"]))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        small_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 8))

    # ---- 1. Case Summary ----
    story.append(Paragraph("1. Case Summary", heading_style))

    complaint = case.complaint if isinstance(case.complaint, dict) else {}

    summary_data = [
        ["Field", "Value"],
        ["case_id", str(case.case_id)],
        ["status", str(case.status)],
        ["jurisdiction", str(getattr(case, "jurisdiction", complaint.get("jurisdiction", "—")))],
        ["risk_level", str(getattr(case, "risk_level", "—"))],
        ["confidence_score", str(getattr(case, "confidence_score", "—"))],
        ["product_name", str(complaint.get("product_name", getattr(case, "product_name", "—")))],
        ["batch_number", str(complaint.get("batch_number", getattr(case, "batch_number", "—")) or "null")],
        ["complaint_type", str(complaint.get("complaint_type", getattr(case, "complaint_type", "—")))],
        ["created_at", str(case.created_at)],
        ["updated_at", str(case.updated_at)],
    ]

    summary_table = Table(summary_data, colWidths=[60 * mm, 110 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f5f5"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # ---- 2. Investigation Output ----
    story.append(Paragraph("2. Investigation Output", heading_style))

    investigation = case.investigation_output if isinstance(case.investigation_output, dict) else {}

    if investigation:
        # Root cause hypotheses
        hypotheses = investigation.get("root_cause_hypotheses", [])
        if hypotheses:
            story.append(Paragraph("<b>Root Cause Hypotheses</b>", body_style))
            for i, h in enumerate(hypotheses, 1):
                if isinstance(h, dict):
                    hyp_text = h.get("hypothesis", str(h))
                    hyp_conf = h.get("confidence", "")
                    story.append(Paragraph(
                        f"{i}. {hyp_text}" + (f" (confidence: {hyp_conf})" if hyp_conf else ""),
                        body_style,
                    ))
                else:
                    story.append(Paragraph(f"{i}. {h}", body_style))
            story.append(Spacer(1, 4))

        # Evidence summary
        evidence = investigation.get("evidence_summary", "")
        if evidence:
            story.append(Paragraph("<b>Evidence Summary</b>", body_style))
            story.append(Paragraph(str(evidence), body_style))
            story.append(Spacer(1, 4))

        # Overall confidence
        overall_conf = investigation.get("overall_confidence", "")
        if overall_conf != "":
            story.append(Paragraph(f"<b>Overall Confidence Score:</b> {overall_conf}", body_style))
            story.append(Spacer(1, 4))

        # Source citations — source_list (Golden Rule field)
        source_list = investigation.get("source_list", [])
        if source_list:
            story.append(Paragraph("<b>Source Citations (source_list)</b>", body_style))
            for src in source_list:
                story.append(Paragraph(f"• {src}", body_style))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No investigation output recorded.", body_style))
        story.append(Spacer(1, 4))

    # ---- 3. CAPA Summary ----
    story.append(Paragraph("3. CAPA Summary", heading_style))

    if capa_records:
        for capa in capa_records:
            story.append(Paragraph(
                f"<b>CAPA ID:</b> {capa.capa_id} &nbsp; "
                f"<b>Status:</b> {capa.status} &nbsp; "
                f"<b>Effectiveness Result:</b> {capa.effectiveness_result or '—'}",
                body_style,
            ))

            actions = capa.actions if isinstance(capa.actions, list) else []
            if actions:
                action_data = [["#", "Type", "Description", "Role", "Due Date", "Status"]]
                for idx, action in enumerate(actions, 1):
                    if isinstance(action, dict):
                        action_data.append([
                            str(idx),
                            action.get("type", "—"),
                            action.get("description", "—"),
                            action.get("responsible_role", "—"),
                            action.get("due_date", "—"),
                            action.get("status", "pending"),
                        ])

                action_table = Table(
                    action_data,
                    colWidths=[8 * mm, 22 * mm, 60 * mm, 28 * mm, 22 * mm, 18 * mm],
                )
                action_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eaf0fb"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(Spacer(1, 4))
                story.append(action_table)

            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No CAPA records found for this case.", body_style))
        story.append(Spacer(1, 4))

    # ---- 4. Complete Audit Trail ----
    story.append(Paragraph("4. Complete Audit Trail", heading_style))

    if audit_events:
        audit_data = [["Timestamp", "Event Type", "Actor", "Stage", "Summary"]]
        for event in audit_events:
            audit_data.append([
                str(event.timestamp.strftime("%Y-%m-%d %H:%M") if event.timestamp else "—"),
                str(event.event_type or "—"),
                str(event.actor or "—"),
                str(getattr(event, "stage", None) or "—"),
                str(event.summary or "—"),
            ])

        audit_table = Table(
            audit_data,
            colWidths=[30 * mm, 30 * mm, 25 * mm, 20 * mm, 65 * mm],
        )
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#533483")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9f5ff"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("WORDWRAP", (4, 1), (4, -1), True),
        ]))
        story.append(audit_table)
    else:
        story.append(Paragraph("No audit events recorded.", body_style))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Paragraph(
        f"QualiTrace AI — Confidential Case Closure Report | {case.case_id} | "
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        small_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ---------------------------------------------------------------------------
# GET /reports/{case_id}
# ---------------------------------------------------------------------------

@router.get("/{case_id}")
def get_case_report(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Retrieve case
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found",
        )

    # Per spec: return 400 if case is not closed
    if case.status != "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Report cannot be generated. Case '{case_id}' has status '{case.status}'. "
                "Reports are only available for closed cases."
            ),
        )

    # Fetch linked CAPA records
    capa_records = (
        db.query(CAPA)
        .filter(CAPA.case_id == case_id)
        .order_by(CAPA.created_at.asc())
        .all()
    )

    # Fetch full audit trail in chronological order
    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.timestamp.asc())
        .all()
    )

    # Build PDF
    try:
        pdf_bytes = _build_pdf(case, capa_records, audit_events)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Log report generation in audit trail
    audit_service.log_event(
        db=db,
        case_id=case_id,
        event_type="report_generated",
        actor=current_user.username,
        stage="closure",
        summary=f"Case closure PDF report generated for '{case_id}' by {current_user.username}",
        payload={
            "case_id": case_id,
            "generated_by": current_user.username,
            "generated_at": datetime.utcnow().isoformat(),
            "capa_count": len(capa_records),
            "audit_event_count": len(audit_events),
        },
    )

    filename = f"QualiTrace_{case_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
