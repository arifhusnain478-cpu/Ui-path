export type Jurisdiction = "US" | "EU";
export type MarketCode = "US" | "EU";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type CaseStatus = "open" | "pending_review" | "closed";
export type ComplaintType = "contamination" | "labeling" | "quality";
export type UserRole = "quality_reviewer" | "quality_lead" | "system_admin";
export type TaskDecision = "approve" | "reject" | "override";

export interface LoginRequest { email: string; password: string; }
export interface AuthUser { user_id: string; username?: string; email?: string; role: UserRole; }
export interface LoginResponse { token: string; user?: AuthUser; user_id?: string; role?: UserRole; }

export interface ComplaintCreateRequest {
  product_name: string;
  batch_number: string | null;
  market_code: MarketCode;
  complaint_type: ComplaintType;
  patient_impact: boolean;
  description: string;
}

export interface ComplaintCreateResponse {
  case_id: string;
  risk_level: RiskLevel;
  status: "open" | "pending_review";
  jurisdiction: Jurisdiction;
  confidence_score: number;
  created_at: string;
}

export interface RootCauseHypothesis {
  rank: number;
  hypothesis: string;
  confidence: number;
  source_ids: string[];
  supporting_evidence: string;
}

export interface InvestigationOutput {
  evidence_summary: string;
  root_cause_hypotheses: RootCauseHypothesis[];
  overall_confidence: number;
  conflicting_sources: unknown[];
  escalation_required: boolean;
  escalation_reason: string | null;
}

export interface CAPAAction {
  description: string;
  type: "corrective" | "preventive";
  responsible_role: string;
  due_date: string;
  evidence_required?: string;
  effectiveness_metric?: string;
  source_citations?: string[];
  status?: "pending" | "complete";
}

export interface CaseRecord {
  case_id: string;
  jurisdiction: Jurisdiction;
  risk_level: RiskLevel;
  confidence_score: number;
  status: CaseStatus;
  product_name: string;
  batch_number: string | null;
  complaint_type: ComplaintType;
  source_list: string[];
  created_at: string;
  updated_at?: string;
  current_stage?: string;
  description?: string;
  patient_impact?: boolean;
  investigation_output?: InvestigationOutput | null;
  capa_plan?: CAPAAction[] | null;
  sla_deadline?: string | null;
  pending_task_id?: string | null;
}

export interface HumanTask {
  task_id: string;
  case_id: string;
  task_type: "missing_info" | "risk_review" | "capa_approval" | "critical_escalation" | "final_closure";
  assigned_role: string;
  sla_deadline: string;
  status: string;
  decision?: TaskDecision | null;
  override_reason?: string | null;
  ai_recommendation?: string;
  confidence_score?: number;
  source_list?: string[];
}

export interface CompleteTaskRequest { decision: TaskDecision; override_reason: string | null; }

export interface AuditEvent {
  event_id?: string;
  case_id: string;
  timestamp: string;
  event_type?: string;
  action?: string;
  actor?: string;
  user?: string;
  stage?: string;
  summary?: string;
  details?: unknown;
  payload?: unknown;
  override_reason?: string | null;
}
