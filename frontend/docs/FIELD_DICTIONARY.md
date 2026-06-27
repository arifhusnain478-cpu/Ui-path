# Field Dictionary

| Field | Type | Allowed values / rule | Notes |
|---|---|---|---|
| `case_id` | string | `C-001`, `C-002`, ... | Never change format in frontend |
| `jurisdiction` | string | `US`, `EU` | Used in case records |
| `risk_level` | string | `low`, `medium`, `high`, `critical` | Shared across case, RAG, Maestro |
| `confidence_score` | number | `0.0` to `1.0` | Display and human-review visibility |
| `status` | string | `open`, `pending_review`, `closed` | No extra values |
| `product_name` | string | free text | Required on complaint submission |
| `batch_number` | string or null | free text or null | Null is valid |
| `complaint_type` | string | `contamination`, `labeling`, `quality` | No other values |
| `source_list` | string[] | filenames and sections | Used for citations |
| `override_reason` | string | free text | Required for override |
| `market_code` | string | `US`, `EU` | Complaint request only |
| `patient_impact` | boolean | true/false | Complaint request |
| `description` | string | free text | Complaint request |
| `created_at` | ISO datetime | backend-provided | Display only |
| `updated_at` | ISO datetime | backend-provided | Display only |
| `sla_deadline` | ISO datetime | backend-provided | Frontend only displays countdown |
| `current_stage` | string | backend/Maestro-provided | Used by StageTracker |

## Important distinction

Complaint submission uses `market_code`. Created and downstream case records use `jurisdiction`.

## Never send camelCase

Do not use `caseId`, `riskLevel`, `confidenceScore`, `sourceList`, `overrideReason`, `marketCode`, or `patientImpact` in API payloads.
