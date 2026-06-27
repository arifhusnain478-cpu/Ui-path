# Frontend Build Order

1. Foundation: Vite, Tailwind, Router, Axios, contracts, constants.
2. Authentication: authStore, auth API, Login, Navbar, protected routes.
3. Dashboard: cases API, caseStore, CaseCard, filters.
4. Complaint submission: exact request contract, null batch_number allowed.
5. Case detail: StageTracker, ConfidenceBadge, CitationCard, HypothesisPanel, CAPATable, SLATimer.
6. Human review: tasks API, HumanTask, OverrideModal, approve/reject/override.
7. Audit trail: chronological rendering only.
8. Verification: Network tab, no camelCase, no direct Axios in components, no hardcoded outcomes, all three scenarios.
