import { useNavigate } from "react-router-dom";
import { APP_ROUTES } from "../config/constants.js";
import {
  displayValue,
  formatComplaintTypeLabel,
  formatDateTime,
  formatSnakeCaseLabel,
  formatStatusLabel,
} from "../utils/display.js";

const risk_styles = {
  critical: "border-red-200 bg-red-50 text-red-700",
  high: "border-rose-200 bg-rose-50 text-rose-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  low: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

const status_styles = {
  open: "border-blue-200 bg-blue-50 text-blue-700",
  pending_review: "border-violet-200 bg-violet-50 text-violet-700",
  closed: "border-[var(--qt-border)] bg-[var(--qt-bg)] text-[var(--qt-text-secondary)]",
};

export default function CaseCard({ case_record }) {
  const navigate = useNavigate();
  const case_id = case_record?.case_id;
  const risk_level = case_record?.risk_level;
  const status = case_record?.status;
  const jurisdiction = case_record?.jurisdiction;
  const is_critical = risk_level === "critical";

  function openCase() {
    if (case_id) {
      navigate(APP_ROUTES.case_detail(case_id));
    }
  }

  return (
    <button
      type="button"
      onClick={openCase}
      disabled={!case_id}
      className={`group w-full border border-[var(--qt-border)] bg-[var(--qt-surface)] p-5 text-left transition-colors hover:bg-[var(--qt-bg)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${
        is_critical ? "border-l-[3px] border-l-[var(--qt-critical)]" : ""
      }`}
      aria-label={`Open case ${displayValue(case_id)}`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="qt-eyebrow">
            {displayValue(case_id)}
          </p>
          <h2 className="mt-1.5 break-words text-lg font-medium tracking-tight text-[var(--qt-text-primary)]">
            {displayValue(case_record?.product_name)}
          </h2>
          {case_record?.current_stage ? (
            <p className="mt-2 text-sm text-[var(--qt-text-secondary)]">
              {case_record.current_stage}
            </p>
          ) : null}
        </div>

        <div className="flex flex-shrink-0 flex-wrap gap-1.5">
          <Badge className={risk_styles[risk_level]}>
            {formatSnakeCaseLabel(risk_level)}
          </Badge>
          <Badge className={status_styles[status]}>{formatStatusLabel(status)}</Badge>
          <Badge className="border-[var(--qt-border)] bg-[var(--qt-bg)] text-[var(--qt-text-secondary)]">
            {displayValue(jurisdiction)}
          </Badge>
        </div>
      </div>

      <div className="mt-4 h-px bg-[var(--qt-border)]" />

      <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <div>
          <dt className="text-xs text-[var(--qt-text-muted)]">Created</dt>
          <dd className="mt-0.5 text-[var(--qt-text-primary)]">
            {formatDateTime(case_record?.created_at)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--qt-text-muted)]">Type</dt>
          <dd className="mt-0.5 text-[var(--qt-text-primary)]">
            {formatComplaintTypeLabel(case_record?.complaint_type)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--qt-text-muted)]">Batch</dt>
          <dd className="mt-0.5 text-[var(--qt-text-primary)]">
            {case_record?.batch_number ? case_record.batch_number : "—"}
          </dd>
        </div>
      </dl>
    </button>
  );
}

function Badge({ children, className }) {
  return (
    <span className={`qt-badge ${className || ""}`}>
      <span className="truncate">{children}</span>
    </span>
  );
}