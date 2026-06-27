# QualiTrace AI Frontend — Codex Operating Rules

This repository implements only the frontend defined in the approved QualiTrace AI Build Guide v1.0 and Test Checklist.

## Source of truth

Use only these approved contracts and rules:

- `docs/FIELD_DICTIONARY.md`
- `docs/API_CONTRACTS.md`
- `docs/FRONTEND_ARCHITECTURE.md`
- `docs/PAGE_SPECIFICATIONS.md`
- `docs/COMPONENT_SPECIFICATIONS.md`
- `docs/STATE_AND_API_RULES.md`
- `docs/FRONTEND_TEST_CHECKLIST.md`
- `src/types/contracts.ts`
- `src/config/constants.js`

Do not invent, rename, remove, or reinterpret shared fields, enum values, endpoints, stages, roles, or workflow behavior.

## Non-negotiable rules

1. Use React + Vite.
2. Use Tailwind CSS, Zustand, Axios, and React Router.
3. Use `snake_case` for every shared field.
4. Never use camelCase for API request or response fields.
5. Components must not call `fetch` or `axios` directly.
6. All HTTP calls must live under `src/api/`.
7. Shared case and authentication state must live in Zustand stores.
8. Do not hardcode backend results in pages or components.
9. Do not invent endpoints.
10. Do not invent statuses, risk levels, jurisdictions, complaint types, roles, or task types.
11. `market_code` is used when submitting a complaint.
12. `jurisdiction` is used in the created case and downstream case data.
13. `override_reason` is required when the reviewer overrides a decision.
14. The frontend must display backend-provided SLA deadlines; it must not calculate SLA policy locally.
15. The frontend must render audit data returned by the backend; it must never create audit events itself.
16. Missing `batch_number` is valid input and must not be blocked by frontend validation.
17. Critical and low-confidence cases must visibly support human review.
18. Preserve all approved field names exactly.

## Required pages

- `/login`
- `/dashboard`
- `/complaints/new`
- `/cases/:case_id`
- `/cases/:case_id/tasks/:task_id`
- `/cases/:case_id/audit`

All routes except `/login` are protected.

## Before changing contracts

Stop and request confirmation before changing any field name, enum value, endpoint path, request body, response shape, stage name, task action, role name, or routing behavior.

## Definition of done

A feature is not complete until:

- request and response fields match the approved contract
- browser DevTools shows `snake_case`
- loading, empty, and error states exist
- no direct HTTP call exists inside a component
- protected-route behavior works
- the relevant test checklist items pass
