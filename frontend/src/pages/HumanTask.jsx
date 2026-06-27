import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import CitationCard from "../components/CitationCard.jsx";
import ConfidenceBadge from "../components/ConfidenceBadge.jsx";
import OverrideModal from "../components/OverrideModal.jsx";
import SLATimer from "../components/SLATimer.jsx";
import { ReviewVisualPlaceholder } from "../components/VisualPlaceholders.jsx";
import { completeTask, getTasks } from "../api/tasks.js";
import { APP_ROUTES, MIN_OVERRIDE_REASON_LENGTH } from "../config/constants.js";
import { useAuthStore } from "../store/authStore.js";
import { useCaseStore } from "../store/caseStore.js";
import {
  displayValue,
  formatRoleLabel,
  formatSnakeCaseLabel,
} from "../utils/display.js";

function getStructuredCitations(task) {
  const candidates = [task?.citations, task?.retrieved_chunks, task?.source_citations];
  return candidates.find((value) => Array.isArray(value)) || [];
}

function getCitationItems(task) {
  const source_list = Array.isArray(task?.source_list) ? task.source_list : [];
  const structured_citations = getStructuredCitations(task);
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

function isTaskCompleted(task) {
  return Boolean(task?.decision);
}

function isTaskCritical(task) {
  return task?.task_type === "critical_escalation";
}

export default function HumanTask() {
  const { case_id, task_id } = useParams();
  const user = useAuthStore((state) => state.user);
  const fetchCase = useCaseStore((state) => state.fetchCase);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [completion_loading, setCompletionLoading] = useState(false);
  const [completion_error, setCompletionError] = useState("");
  const [approve_open, setApproveOpen] = useState(false);
  const [reject_reason, setRejectReason] = useState("");
  const [reject_error, setRejectError] = useState("");
  const [override_open, setOverrideOpen] = useState(false);
  const [override_reason, setOverrideReason] = useState("");
  const [override_error, setOverrideError] = useState("");

  const task = useMemo(
    () => tasks.find((item) => item?.task_id === task_id),
    [task_id, tasks],
  );
  const citations = getCitationItems(task);
  const completed = isTaskCompleted(task);

  async function loadTaskList() {
    setLoading(true);
    setError("");

    try {
      const next_tasks = await getTasks(case_id);
      setTasks(next_tasks);
      setError("");
    } catch (load_error) {
      setTasks([]);
      setError(load_error?.message || "Tasks could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTaskList();
  }, [case_id]);

  async function refreshAfterCompletion() {
    const next_tasks = await getTasks(case_id);
    setTasks(next_tasks);
    await fetchCase(case_id);
  }

  async function submitCompletion(decision, reason) {
    if (completion_loading) {
      return;
    }

    setCompletionLoading(true);
    setCompletionError("");
    setSuccess("");

    try {
      await completeTask(task_id, {
        decision,
        override_reason: decision === "approve" ? null : reason.trim(),
      });
      await refreshAfterCompletion();
      setApproveOpen(false);
      setOverrideOpen(false);
      setOverrideReason("");
      setRejectReason("");
      setSuccess("Task completion was submitted.");
    } catch (submit_error) {
      setCompletionError(
        submit_error?.message || "Task completion could not be submitted.",
      );
    } finally {
      setCompletionLoading(false);
    }
  }

  function handleReject() {
    const trimmed_reason = reject_reason.trim();

    if (trimmed_reason.length < MIN_OVERRIDE_REASON_LENGTH) {
      setRejectError(
        `Reject reason must be at least ${MIN_OVERRIDE_REASON_LENGTH} characters.`,
      );
      return;
    }

    setRejectError("");
    submitCompletion("reject", trimmed_reason);
  }

  function handleOverrideSubmit() {
    const trimmed_reason = override_reason.trim();

    if (trimmed_reason.length < MIN_OVERRIDE_REASON_LENGTH) {
      setOverrideError(
        `Override reason must be at least ${MIN_OVERRIDE_REASON_LENGTH} characters.`,
      );
      return;
    }

    setOverrideError("");
    submitCompletion("override", trimmed_reason);
  }

  const is_critical = isTaskCritical(task);

  return (
    <main className="qt-page">
      <div className="qt-container">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              to={APP_ROUTES.case_detail(case_id)}
              className="text-sm text-[var(--qt-text-muted)] transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)]"
            >
              ← Case {displayValue(case_id)}
            </Link>
            <h1 className="mt-3 text-2xl font-normal tracking-tight text-[var(--qt-text-primary)]">
              Task {displayValue(task_id)}
            </h1>
            <p className="mt-1 text-sm text-[var(--qt-text-muted)]">
              Role: {formatRoleLabel(user?.role)}
            </p>
          </div>
          <Link
            to={APP_ROUTES.audit_trail(case_id)}
            className="qt-action-secondary px-4 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2"
          >
            Audit Trail
          </Link>
        </div>

        {loading ? <LoadingState /> : null}
        {!loading && error ? <ErrorState message={error} onRetry={loadTaskList} /> : null}
        {!loading && !error && !task ? <NotFoundState /> : null}

        {!loading && !error && task ? (
          <div className="mt-8 space-y-6">
            {success ? (
              <div
                role="status"
                className="border-l-2 border-[var(--qt-success)] bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
              >
                {success}
              </div>
            ) : null}

            {completion_error ? (
              <div
                role="alert"
                className="border-l-2 border-[var(--qt-critical)] bg-red-50 px-4 py-3 text-sm text-red-800"
              >
                {completion_error}
              </div>
            ) : null}

            {/* Task Header */}
            <section className={`border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6 sm:p-8 ${is_critical ? "border-l-[3px] border-l-[var(--qt-critical)]" : ""}`}>
              <div className="grid gap-8 lg:grid-cols-[1fr_0.85fr]">
                <div>
                  <p className="qt-eyebrow">Case {displayValue(task.case_id)}</p>
                  <h2 className="qt-page-heading mt-3">
                    {formatSnakeCaseLabel(task.task_type)}
                  </h2>
                  <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
                    <DetailItem label="Task ID" value={task.task_id} />
                    <DetailItem label="Case ID" value={task.case_id} />
                    <DetailItem label="Assigned role" value={formatRoleLabel(task.assigned_role)} />
                    <DetailItem label="Task status" value={formatSnakeCaseLabel(task.status)} />
                    {task.decision !== undefined ? (
                      <DetailItem label="Decision" value={formatSnakeCaseLabel(task.decision)} />
                    ) : null}
                    {task.override_reason !== undefined ? (
                      <DetailItem label="Override reason" value={task.override_reason} />
                    ) : null}
                  </dl>
                </div>
                <div className="space-y-4">
                  <ReviewVisualPlaceholder />
                  {task.confidence_score !== undefined ? (
                    <ConfidenceBadge confidence_score={task.confidence_score} />
                  ) : null}
                </div>
              </div>

              {task.ai_recommendation ? (
                <div className="mt-8 border-l-2 border-blue-300 bg-blue-50 py-3 pl-4 pr-4">
                  <h3 className="text-xs font-medium text-blue-600">AI Recommendation</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-blue-900">
                    {task.ai_recommendation}
                  </p>
                </div>
              ) : null}
            </section>

            {/* Citations and SLA */}
            <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
              <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
                <h2 className="qt-section-heading">Citations</h2>
                {citations.string_citations.length > 0 || citations.structured_citations.length > 0 ? (
                  <div className="mt-5 space-y-6">
                    {citations.structured_citations.length > 0 ? (
                      <div>
                        <h3 className="qt-eyebrow mb-3">Structured citations</h3>
                        <div className="space-y-3">
                          {citations.structured_citations.map((citation, index) => (
                            <CitationCard key={`structured-${index}`} citation={citation} />
                          ))}
                        </div>
                      </div>
                    ) : null}
                    {citations.string_citations.length > 0 ? (
                      <div>
                        <h3 className="qt-eyebrow mb-3">Source references</h3>
                        <div className="space-y-2">
                          {citations.string_citations.map((citation) => (
                            <CitationCard key={citation} citation={citation} />
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-[var(--qt-text-muted)]">
                    No citations were returned.
                  </p>
                )}
              </section>
              {completed ? (
                <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
                  <h2 className="qt-section-heading">SLA</h2>
                  <p className="mt-4 text-sm text-[var(--qt-text-muted)]">
                    Task completed.
                  </p>
                </section>
              ) : (
                <SLATimer sla_deadline={task.sla_deadline} />
              )}
            </div>

            {/* Reviewer Actions */}
            <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
              <h2 className="qt-section-heading">Reviewer Actions</h2>
              {completed ? (
                <p className="mt-4 text-sm text-[var(--qt-text-muted)]">
                  This task is read-only because a decision has been recorded.
                </p>
              ) : (
                <div className="mt-5 space-y-6">
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => setApproveOpen(true)}
                      disabled={completion_loading}
                      className="qt-action-primary bg-emerald-600 px-5 py-2.5 hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => setOverrideOpen(true)}
                      disabled={completion_loading}
                      className="qt-action-secondary px-5 py-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Override
                    </button>
                  </div>

                  <div className="border border-[var(--qt-border)] bg-[var(--qt-bg)] p-4">
                    <label
                      htmlFor="reject_reason"
                      className="block text-sm font-medium text-[var(--qt-text-primary)]"
                    >
                      Reject with reason
                    </label>
                    <textarea
                      id="reject_reason"
                      value={reject_reason}
                      onChange={(event) => {
                        setRejectReason(event.target.value);
                        setRejectError("");
                      }}
                      rows={3}
                      disabled={completion_loading}
                      aria-invalid={Boolean(reject_error)}
                      aria-describedby="reject_reason_help reject_reason_count reject_reason_error"
                      className="qt-field mt-2 block resize-y px-3 py-2.5 text-sm disabled:cursor-not-allowed disabled:bg-[var(--qt-bg)]"
                    />
                    <div className="mt-2 flex items-center justify-between text-xs text-[var(--qt-text-muted)]">
                      <span>Minimum {MIN_OVERRIDE_REASON_LENGTH} characters</span>
                      <span>{reject_reason.trim().length} / {MIN_OVERRIDE_REASON_LENGTH}</span>
                    </div>
                    {reject_error ? (
                      <p
                        id="reject_reason_error"
                        className="mt-2 text-sm text-red-700"
                      >
                        {reject_error}
                      </p>
                    ) : null}
                    <button
                      type="button"
                      onClick={handleReject}
                      disabled={
                        reject_reason.trim().length < MIN_OVERRIDE_REASON_LENGTH ||
                        completion_loading
                      }
                      className="mt-3 border border-red-300 bg-[var(--qt-surface)] px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {completion_loading ? "Submitting..." : "Reject"}
                    </button>
                  </div>
                </div>
              )}
            </section>
          </div>
        ) : null}

        {approve_open ? (
          <ApproveDialog
            loading={completion_loading}
            onCancel={() => setApproveOpen(false)}
            onConfirm={() => submitCompletion("approve", "")}
          />
        ) : null}

        <OverrideModal
          open={override_open}
          reason={override_reason}
          error={override_error || completion_error}
          loading={completion_loading}
          onReasonChange={(value) => {
            setOverrideReason(value);
            setOverrideError("");
            setCompletionError("");
          }}
          onCancel={() => setOverrideOpen(false)}
          onSubmit={handleOverrideSubmit}
        />
      </div>
    </main>
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

function LoadingState() {
  return (
    <div className="mt-8 py-12 text-center text-sm text-[var(--qt-text-muted)]">
      Loading task...
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
      The requested task was not found for this case.
    </div>
  );
}

function ApproveDialog({ loading, onCancel, onConfirm }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--qt-text-primary)]/50 px-4 py-6">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="approve_dialog_title"
        className="w-full max-w-sm border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6"
      >
        <h2 id="approve_dialog_title" className="text-lg font-medium text-[var(--qt-text-primary)]">
          Approve Task
        </h2>
        <p className="mt-3 text-sm text-[var(--qt-text-secondary)]">
          Confirm approval. This records the decision as approved.
        </p>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="qt-action-secondary px-4 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="qt-action-primary bg-emerald-600 px-4 py-2 hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Submitting..." : "Confirm"}
          </button>
        </div>
      </section>
    </div>
  );
}