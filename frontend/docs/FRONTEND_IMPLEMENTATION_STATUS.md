# Frontend Implementation Status

## Completed Pages

- `/login`: authenticated login, loading state, visible error state, local auth persistence.
- `/dashboard`: case list, approved filters, loading/error/empty states, case navigation.
- `/complaints/new`: exact complaint request contract, optional `batch_number`, success navigation.
- `/cases/:case_id`: direct case retrieval, case header, investigation, hypotheses, citations, CAPA, SLA, task/audit links.
- `/cases/:case_id/tasks/:task_id`: task list retrieval, route task selection, approve/reject/override completion.
- `/cases/:case_id/audit`: audit retrieval, chronological timeline, unordered events section, safe details/payload rendering.

## Completed Components

- `Navbar`
- `ProtectedRoute`
- `CaseCard`
- `StageTracker`
- `ConfidenceBadge`
- `HypothesisPanel`
- `CitationCard`
- `CAPATable`
- `SLATimer`
- `OverrideModal`

## Completed API Adapters

- `src/api/client.js`: shared Axios client, `VITE_API_BASE_URL`, Bearer token injection, optional mock adapter.
- `src/api/auth.js`: login and register wrappers; login normalizes only documented response variants.
- `src/api/cases.js`: complaints list, single case, complaint create, audit trail, status update, report blob wrapper.
- `src/api/tasks.js`: task list and task completion wrappers.
- `src/api/mockAdapter.js`: opt-in local mock API behind `VITE_USE_MOCK_API=true`.

## Completed Zustand Stores

- `authStore`: `token`, `user`, `isAuthenticated`, `isHydrated`, `loading`, `error`; login, logout, storage hydration.
- `caseStore`: `cases`, `currentCase`, `loading`, `error`, `filters`; case list and current-case loading.

## Supported Routes

- `/login`
- `/dashboard`
- `/complaints/new`
- `/cases/:case_id`
- `/cases/:case_id/tasks/:task_id`
- `/cases/:case_id/audit`

All routes except `/login` are protected.

## Supported Request/Response Contracts

- `POST /auth/login`
- `POST /auth/register`
- `GET /complaints`
- `POST /complaints`
- `GET /complaints/{case_id}`
- `PUT /cases/{case_id}/status`
- `GET /cases/{case_id}/audit`
- `GET /tasks?case_id={case_id}`
- `PUT /tasks/{task_id}/complete`
- `GET /reports/{case_id}` as a blob wrapper only

No approved shared contract fields were changed.

## Known Backend-Dependent Ambiguities

- Exact ordered stage schema is not fixed. The UI uses a backend `stages` array only if provided; otherwise it displays `current_stage`.
- Structured citation locations are not fixed. The UI renders only returned `source_list`, `citations`, `retrieved_chunks`, or `source_citations` fields.
- Task `status` values are not fixed. Read-only task state is based on returned `decision`, not invented status meanings.
- Backend error response shapes are not fixed. The UI shows visible generic errors where a contract-specific error body is unavailable.
- Audit event category vocabulary is not fixed. Styling remains neutral unless returned fields indicate AI, human, override, system, stage, or SLA.

## Manual Testing Performed

- `npm run build` completed successfully.
- `VITE_USE_MOCK_API=true VITE_API_BASE_URL=http://localhost:8000 npm run build` completed successfully.
- `npm run lint` was attempted; no lint script is configured.
- Contract search for forbidden shared camelCase field names found no app-code hits.
- Direct HTTP search confirmed Axios appears only in `src/api/client.js`; no `fetch` calls were found.
- Hardcoded URL search found no app-code localhost URLs; only the approved docs example remains.
- Console logging search found no `console.*` calls in `src`.
- Browser mock-mode verification at 375px, 768px, and 1440px covered `/dashboard`, `/complaints/new`, `/cases/C-001`, `/cases/C-003/tasks/T-003`, and `/cases/C-003/audit`.
- Browser mock-mode scenario checks covered normal case display, missing-batch complaint submission, and critical override flow with audit display.

## Build Result

- Production build: pass.
- Mock-mode production build: pass.
- Lint: not run because no `lint` script exists in `package.json`.

## Remaining Integration Steps

- Connect to the real backend and verify live network payloads in browser DevTools.
- Confirm backend response wrappers match the strict adapter allowlists.
- Confirm Maestro-provided stage data shape if ordered stage display is required.
- Confirm structured citation field locations and names.
- Confirm task completion refresh behavior against live backend state.
- Confirm audit event vocabulary and payload shape with live backend events.
