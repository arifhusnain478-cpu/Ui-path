export const JURISDICTIONS = ["US", "EU"];
export const RISK_LEVELS = ["low", "medium", "high", "critical"];
export const CASE_STATUSES = ["open", "pending_review", "closed"];
export const COMPLAINT_TYPES = ["contamination", "labeling", "quality"];
export const TASK_DECISIONS = ["approve", "reject", "override"];
export const USER_ROLES = ["quality_reviewer", "quality_lead", "system_admin"];
export const CONFIDENCE_THRESHOLDS = { high: 0.85, warning: 0.70, low: 0.60 };
export const MIN_OVERRIDE_REASON_LENGTH = 10;
export const APP_ROUTES = {
  login: "/login",
  dashboard: "/dashboard",
  new_complaint: "/complaints/new",
  case_detail: (case_id) => `/cases/${case_id}`,
  human_task: (case_id, task_id) => `/cases/${case_id}/tasks/${task_id}`,
  audit_trail: (case_id) => `/cases/${case_id}/audit`,
};
