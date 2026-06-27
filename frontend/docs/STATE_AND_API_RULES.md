# State and API Rules

## Axios

Use one shared Axios instance with `VITE_API_BASE_URL` and Bearer token injection.

## API modules

`auth.js`: login, register.

`cases.js`: getCases, getCase, getAuditTrail, createComplaint, updateCaseStatus only if required.

`tasks.js`: getTasks, completeTask.

## Auth store

State: token, user, isAuthenticated.

Actions: setToken, setUser, clearToken, logout, hydrateFromStorage.

## Case store

State: cases, currentCase, loading, error.

Actions: fetchCases, fetchCase, refreshCurrentCase, clearError.

## UI states

Every API-driven page must have loading and error states; list pages also need empty states.

## Mocking

Use one contract-safe mock adapter or dataset. Never embed mock data in components.
