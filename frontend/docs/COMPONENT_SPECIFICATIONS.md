# Component Specifications

## Navbar

App identity, user, role, New Complaint, Logout.

## CaseCard

case_id, product_name, risk_level, status, jurisdiction, created_at.

## StageTracker

Seven connected stages; current highlighted, completed distinct, future dimmed. Use backend current_stage.

## ConfidenceBadge

- > 0.85 green
- 0.70–0.84 orange
- < 0.70 red
- < 0.60 clearly low confidence

## HypothesisPanel

Exactly 3 hypotheses where available, each with rank, text, confidence, sources, evidence.

## CitationCard

Source, section, authority if returned, full text only if returned.

## CAPATable

Type, description, responsible role, due date, status, evidence.

## SLATimer

Read backend `sla_deadline`; display countdown; red when breached. Do not calculate SLA policy.

## OverrideModal

`override_reason`, minimum 10 characters, disabled submit until valid, exact snake_case payload.
