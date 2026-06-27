# QualiTrace AI Frontend Reference Pack

This pack is the implementation guardrail for the QualiTrace AI React frontend.

It is intentionally limited to the approved Build Guide v1.0 and Test Checklist. It does not add new product scope.

## Start here

1. Read `AGENTS.md`.
2. Read `docs/FIELD_DICTIONARY.md`.
3. Read `docs/API_CONTRACTS.md`.
4. Read `docs/FRONTEND_ARCHITECTURE.md`.
5. Build in the order listed in `docs/BUILD_ORDER.md`.
6. Validate every page against `docs/FRONTEND_TEST_CHECKLIST.md`.

## Technical stack

- React + Vite
- Tailwind CSS
- Zustand
- Axios
- React Router

## Golden rule

All shared fields must use `snake_case` and must match the backend, RAG pipeline, and Maestro case schema exactly.

## Core distinction

- Complaint submission uses `market_code`.
- Created and downstream case records use `jurisdiction`.

Do not merge or rename these fields.

## Reference implementation assets

- `src/types/contracts.ts`
- `src/config/constants.js`
- `src/mocks/contract_safe_examples.json`
- `.env.example`
