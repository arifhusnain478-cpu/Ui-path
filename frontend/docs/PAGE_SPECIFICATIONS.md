# Page Specifications

## `/login`

- email/password
- POST `/auth/login`
- store JWT
- redirect to Dashboard
- error on failure

## `/dashboard`

- case list
- jurisdiction/status/risk filters
- show case_id, product_name, risk_level, status, jurisdiction, created_at
- empty/loading/error states

## `/complaints/new`

Fields: product_name, batch_number optional, market_code, complaint_type, patient_impact, description.

## `/cases/:case_id`

Show case header, status, risk, jurisdiction, confidence, stage, investigation, 3 hypotheses, citations, CAPA, SLA, task link, audit link.

## `/cases/:case_id/tasks/:task_id`

Show task details, AI recommendation, confidence, citations, SLA, Approve, Reject, Override, and Escalate only if supported by returned contract.

## `/cases/:case_id/audit`

Chronological audit events with visible AI, human, override, system, stage transition, and SLA distinctions.
