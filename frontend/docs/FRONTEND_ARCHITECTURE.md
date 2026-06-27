# Frontend Architecture

## Stack

- React + Vite
- Tailwind CSS
- Zustand
- Axios
- React Router

## Required structure

```text
src/
├── api/
│   ├── auth.js
│   ├── cases.js
│   └── tasks.js
├── components/
│   ├── Navbar.jsx
│   ├── CaseCard.jsx
│   ├── StageTracker.jsx
│   ├── ConfidenceBadge.jsx
│   ├── HypothesisPanel.jsx
│   ├── CitationCard.jsx
│   ├── CAPATable.jsx
│   ├── SLATimer.jsx
│   └── OverrideModal.jsx
├── pages/
│   ├── Login.jsx
│   ├── Dashboard.jsx
│   ├── NewComplaint.jsx
│   ├── CaseDetail.jsx
│   ├── HumanTask.jsx
│   └── AuditTrail.jsx
├── store/
│   ├── authStore.js
│   └── caseStore.js
├── types/contracts.ts
├── config/constants.js
├── App.jsx
└── main.jsx
```

## HTTP boundary

Only files inside `src/api/` may call Axios.

## State boundary

`authStore.js` owns authentication state. `caseStore.js` owns case list/current case/loading/error state.

## Environment

```text
VITE_API_BASE_URL=http://localhost:8000
```

Do not hardcode API URLs inside components.

## Protected routes

All routes except `/login` require authentication.
