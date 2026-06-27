# API Contracts

Do not invent endpoints or change these shapes without team approval.

## POST `/auth/register`

Request:

```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "role": "quality_reviewer"
}
```

## POST `/auth/login`

```json
{
  "email": "string",
  "password": "string"
}
```

Store returned JWT and role data.

## POST `/complaints`

Request:

```json
{
  "product_name": "Metformin 500mg",
  "batch_number": "MF-2024-0892",
  "market_code": "US",
  "complaint_type": "quality",
  "patient_impact": false,
  "description": "Tablet has unusual smell"
}
```

`batch_number` may be `null`.

Response:

```json
{
  "case_id": "C-001",
  "risk_level": "medium",
  "status": "open",
  "jurisdiction": "US",
  "confidence_score": 0.82,
  "created_at": "2026-06-27T10:00:00Z"
}
```

## GET `/complaints`

Optional filters: `jurisdiction`, `status`, `risk_level`.

## GET `/complaints/{case_id}`

Returns full case object.

## PUT `/cases/{case_id}/status`

Updates valid status only.

## GET `/cases/{case_id}/audit`

Returns chronological audit trail.

## GET `/tasks?case_id={case_id}`

Returns case tasks.

## PUT `/tasks/{task_id}/complete`

Approve:

```json
{"decision":"approve","override_reason":null}
```

Reject:

```json
{"decision":"reject","override_reason":"Required reviewer reason"}
```

Override:

```json
{"decision":"override","override_reason":"Required explanation with at least 10 characters"}
```

## POST `/capa`

Creates CAPA linked to `case_id`.

## PUT `/capa/{capa_id}/effectiveness`

Records effectiveness after actions complete.

## GET `/reports/{case_id}`

Returns final PDF report. Must not run while case is open.

## POST `/webhook/maestro`

Frontend does not call this endpoint.
