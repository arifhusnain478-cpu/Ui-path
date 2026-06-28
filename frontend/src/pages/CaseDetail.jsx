import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import CAPATable from "../components/CAPATable.jsx";
import CitationCard from "../components/CitationCard.jsx";
import ConfidenceBadge from "../components/ConfidenceBadge.jsx";
import HypothesisPanel from "../components/HypothesisPanel.jsx";
import SLATimer from "../components/SLATimer.jsx";
import StageTracker from "../components/StageTracker.jsx";
import { CaseVisualPlaceholder } from "../components/VisualPlaceholders.jsx";
import { APP_ROUTES } from "../config/constants.js";
import { useCaseStore } from "../store/caseStore.js";
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

function getStructuredCitations(case_record) {
  const candidates = [
    case_record?.citations,
    case_record?.retrieved_chunks,
    case_record?.source_citations,
    case_record?.investigation_output?.citations,
    case_record?.investigation_output?.retrieved_chunks,
  ];

  return candidates.find((value) => Array.isArray(value)) || [];
}

function getCitationItems(case_record) {
  const source_list = Array.isArray(case_record?.source_list)
    ? case_record.source_list
    : [];
  const structured_citations = getStructuredCitations(case_record);
  const structured_sources = new Set(
    structured_citations
      .map((citation) => citation?.source)
      .filter((source) => typeof source === "string" && source.length > 0),
  );
  const string_citations = source_list.filter(
    (source) =>
      !Array.from(structured_sources).some(
        (structured_source) =>
          source === structured_source || source.startsWith(`${structured_source}#`),
      ),
  );

  return { string_citations, structured_citations };
}

export default function CaseDetail() {
  const { case_id } = useParams();
  const currentCase = useCaseStore((state) => state.currentCase);
  const loading = useCaseStore((state) => state.loading);
  const error = useCaseStore((state) => state.error);
  const fetchCase = useCaseStore((state) => state.fetchCase);
  const clearCurrentCase = useCaseStore((state) => state.clearCurrentCase);

  useEffect(() => {
    fetchCase(case_id);
    return () => clearCurrentCase();
  }, [case_id, clearCurrentCase, fetchCase]);

  function handleRetry() {
    fetchCase(case_id);
  }

  const citation_items = getCitationItems(currentCase);
  const is_critical = currentCase?.risk_level === "critical";

  return (
    <main className="qt-page">
      <div className="qt-container">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              to={APP_ROUTES.dashboard}
              className="text-sm text-[var(--qt-text-muted)] transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)]"
            >
              ← Dashboard
            </Link>
            <h1 className="mt-3 text-2xl font-normal tracking-tight text-[var(--qt-text-primary)]">
              Case {displayValue(case_id)}
            </h1>
          </div>

          {currentCase ? (
            <div className="flex flex-wrap gap-2">
              {currentCase.pending_task_id ? (
                <Link
                  to={APP_ROUTES.human_task(currentCase.case_id, currentCase.pending_task_id)}
                  className="qt-action-primary px-4 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2"
                >
                  Open Pending Task
                </Link>
              ) : null}
              <Link
                to={APP_ROUTES.audit_trail(currentCase.case_id)}
                className="qt-action-secondary px-4 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2"
              >
                Audit Trail
              </Link>
            </div>
          ) : null}
        </div>

        {loading ? <LoadingState /> : null}

        {!loading && error ? <ErrorState message={error} onRetry={handleRetry} /> : null}

        {!loading && !error && !currentCase ? <NotFoundState /> : null}

        {!loading && !error && currentCase ? (
          <div className="mt-8 space-y-8">
            {/* Case Header Section */}
            <section className={`border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6 sm:p-8 ${is_critical ? "border-l-[3px] border-l-[var(--qt-critical)]" : ""}`}>
              <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
                <div>
                  <p className="qt-eyebrow">{displayValue(currentCase.case_id)}</p>
                  <h2 className="qt-page-heading mt-3">
                    {displayValue(currentCase.product_name)}
                  </h2>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Badge className={risk_styles[currentCase.risk_level]}>
                      {formatSnakeCaseLabel(currentCase.risk_level)}
                    </Badge>
                    <Badge className={status_styles[currentCase.status]}>
                      {formatStatusLabel(currentCase.status)}
                    </Badge>
                    <Badge className="border-[var(--qt-border)] bg-[var(--qt-bg)] text-[var(--qt-text-secondary)]">
                      {displayValue(currentCase.jurisdiction)}
                    </Badge>
                  </div>
                  {currentCase.description ? (
                    <div className="mt-6">
                      <p className="qt-copy whitespace-pre-wrap text-sm">
                        {currentCase.description}
                      </p>
                    </div>
                  ) : null}
                </div>
                <div className="space-y-4">
                  <CaseVisualPlaceholder
                    risk_level={currentCase.risk_level}
                    product_name={currentCase.product_name}
                  />
                  <ConfidenceBadge confidence_score={currentCase.confidence_score} />
                </div>
              </div>

              <div className="mt-8 h-px bg-[var(--qt-border)]" />

              <dl className="mt-6 grid gap-6 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <DetailItem label="Batch number" value={currentCase.batch_number} />
                <DetailItem label="Complaint type" value={formatComplaintTypeLabel(currentCase.complaint_type)} />
                <DetailItem label="Jurisdiction" value={currentCase.jurisdiction} />
                <DetailItem label="Created" value={formatDateTime(currentCase.created_at)} />
                {currentCase.updated_at !== undefined ? (
                  <DetailItem label="Updated" value={formatDateTime(currentCase.updated_at)} />
                ) : null}
                {currentCase.patient_impact !== undefined ? (
                  <DetailItem label="Patient impact" value={currentCase.patient_impact} />
                ) : null}
              </dl>
            </section>

            {/* Stage and SLA */}
            <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
              <StageTracker
                current_stage={currentCase.current_stage}
                stages={currentCase.stages}
              />
              <SLATimer sla_deadline={currentCase.sla_deadline} />
            </div>

            {/* Investigation */}
            <InvestigationSummary investigation_output={currentCase.investigation_output} />
            <HypothesisPanel investigation_output={currentCase.investigation_output} />

            {/* Citations */}
            <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
              <h2 className="qt-section-heading">Citations</h2>
              {citation_items.string_citations.length > 0 || citation_items.structured_citations.length > 0 ? (
                <div className="mt-5 space-y-6">
                  {citation_items.structured_citations.length > 0 ? (
                    <div>
                      <h3 className="qt-eyebrow mb-3">Structured citations</h3>
                      <div className="space-y-3">
                        {citation_items.structured_citations.map((citation, index) => (
                          <CitationCard key={`structured-${index}`} citation={citation} />
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {citation_items.string_citations.length > 0 ? (
                    <div>
                      <h3 className="qt-eyebrow mb-3">Source references</h3>
                      <div className="space-y-2">
                        {citation_items.string_citations.map((citation) => (
                          <CitationCard key={citation} citation={citation} />
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="mt-4 text-sm text-[var(--qt-text-muted)]">No citations were returned.</p>
              )}
            </section>

            {/* CAPA */}
            <CAPATable capa_plan={currentCase.capa_plan} />
          </div>
        ) : null}
      </div>
    </main>
  );
}

function Badge({ children, className }) {
  return (
    <span className={`qt-badge ${className || ""}`}>
      <span className="truncate">{children}</span>
    </span>
  );
}

function DetailItem({ label, value }) {
  return (
    <div>
      <dt className="text-xs text-[var(--qt-text-muted)]">{label}</dt>
      <dd className="mt-1 break-words font-medium text-[var(--qt-text-primary)]">{displayValue(value)}</dd>
    </div>
  );
}

function InvestigationSummary({ investigation_output }) {
  if (!investigation_output || Object.keys(investigation_output).length === 0) {
    return (
      <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
        <h2 className="qt-section-heading">Investigation</h2>
        <p className="mt-4 text-sm text-[var(--qt-text-muted)]">No investigation output was returned.</p>
      </section>
    );
  }

  return (
    <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
      <h2 className="qt-section-heading">Investigation</h2>
      {investigation_output.evidence_summary ? (
        <p className="qt-copy mt-4 whitespace-pre-wrap text-sm">
          {investigation_output.evidence_summary}
        </p>
      ) : (
        <p className="mt-4 text-sm text-[var(--qt-text-muted)]">Evidence summary was not returned.</p>
      )}
      {investigation_output.overall_confidence !== undefined ? (
        <div className="mt-5 max-w-sm">
          <ConfidenceBadge
            confidence_score={investigation_output.overall_confidence}
            label="Investigation confidence"
          />
        </div>
      ) : null}
      {investigation_output.escalation_required !== undefined ? (
        <p className="mt-5 text-sm text-[var(--qt-text-secondary)]">
          <span className="font-medium">Escalation required:</span> {displayValue(investigation_output.escalation_required)}
        </p>
      ) : null}
      {investigation_output.escalation_reason ? (
        <p className="mt-2 text-sm text-[var(--qt-text-secondary)]">
          {investigation_output.escalation_reason}
        </p>
      ) : null}
    </section>
  );
}

function LoadingState() {
  return (
    <div className="mt-8 py-12 text-center text-sm text-[var(--qt-text-muted)]">
      Loading case...
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="mt-8 border-l-2 border-[var(--qt-critical)] bg-red-50 px-4 py-4">
      <p className="text-sm text-red-800">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-sm font-medium text-red-700 underline underline-offset-2 hover:text-red-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
      >
        Retry
      </button>
    </div>
  );
}

function NotFoundState() {
  return (
    <div className="mt-8 py-12 text-center text-sm text-[var(--qt-text-muted)]">
      Case data is not available.
    </div>
  );
}