import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAuditTrail } from "../api/cases.js";
import { APP_ROUTES } from "../config/constants.js";
import {
  displayValue,
  formatDateTime,
  formatSnakeCaseLabel,
} from "../utils/display.js";

function getTimeValue(timestamp) {
  if (typeof timestamp !== "string" || timestamp.trim().length === 0) {
    return null;
  }

  const value = new Date(timestamp).getTime();
  return Number.isNaN(value) ? null : value;
}

function getEventLabel(event) {
  return formatSnakeCaseLabel(event.event_type || event.action || "Audit event");
}

function getActorLabel(event) {
  return event.actor || event.user || "";
}

function getEventTone(event) {
  const type_action_text = `${event.event_type || ""} ${event.action || ""}`.toLowerCase();
  const full_text = `${type_action_text} ${event.actor || ""} ${event.user || ""}`.toLowerCase();

  if (event.override_reason || type_action_text.includes("override")) {
    return {
      label: "Override",
      marker_color: "bg-[var(--qt-critical)]",
      badge_class: "border-red-200 bg-red-50 text-red-700",
    };
  }

  if (full_text.includes("ai")) {
    return {
      label: "AI decision",
      marker_color: "bg-violet-500",
      badge_class: "border-violet-200 bg-violet-50 text-violet-700",
    };
  }

  if (full_text.includes("human") || full_text.includes("reviewer") || full_text.includes("user")) {
    return {
      label: "Human decision",
      marker_color: "bg-blue-500",
      badge_class: "border-blue-200 bg-blue-50 text-blue-700",
    };
  }

  if (full_text.includes("stage") || event.stage) {
    return {
      label: "Stage transition",
      marker_color: "bg-teal-500",
      badge_class: "border-teal-200 bg-teal-50 text-teal-700",
    };
  }

  if (full_text.includes("sla")) {
    return {
      label: "SLA event",
      marker_color: "bg-[var(--qt-warning)]",
      badge_class: "border-amber-200 bg-amber-50 text-amber-700",
    };
  }

  if (full_text.includes("system")) {
    return {
      label: "System action",
      marker_color: "bg-[var(--qt-text-muted)]",
      badge_class: "border-[var(--qt-border)] bg-[var(--qt-bg)] text-[var(--qt-text-secondary)]",
    };
  }

  return {
    label: "Event",
    marker_color: "bg-[var(--qt-border)]",
    badge_class: "border-[var(--qt-border)] bg-[var(--qt-surface)] text-[var(--qt-text-secondary)]",
  };
}

function renderStructuredValue(value) {
  if (value === undefined) {
    return null;
  }

  if (typeof value === "string") {
    return value;
  }

  if (value === null || typeof value === "number" || typeof value === "boolean") {
    return JSON.stringify(value);
  }

  return JSON.stringify(value, null, 2);
}

export default function AuditTrail() {
  const { case_id } = useParams();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAuditTrail() {
    setLoading(true);
    setError("");

    try {
      const audit_events = await getAuditTrail(case_id);
      setEvents(audit_events);
    } catch (audit_error) {
      setEvents([]);
      setError(
        audit_error?.response?.status === 404
          ? "Case audit trail not found."
          : audit_error?.message || "Audit trail could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAuditTrail();
  }, [case_id]);

  const { chronological_events, unordered_events } = useMemo(() => {
    const with_valid_time = [];
    const without_valid_time = [];

    events.forEach((event, index) => {
      const time_value = getTimeValue(event.timestamp);

      if (time_value === null) {
        without_valid_time.push({ event, index });
      } else {
        with_valid_time.push({ event, index, time_value });
      }
    });

    with_valid_time.sort((a, b) => a.time_value - b.time_value || a.index - b.index);

    return {
      chronological_events: with_valid_time,
      unordered_events: without_valid_time,
    };
  }, [events]);

  return (
    <main className="min-h-screen bg-[var(--qt-bg)] py-10">
      <div className="mx-auto max-w-4xl px-6">
        {/* Navigation */}
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          <Link
            to={APP_ROUTES.case_detail(case_id)}
            className="text-[var(--qt-text-secondary)] underline underline-offset-2 transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)]"
          >
            ← Case Detail
          </Link>
          <span className="text-[var(--qt-text-muted)]">·</span>
          <Link
            to={APP_ROUTES.dashboard}
            className="text-[var(--qt-text-secondary)] underline underline-offset-2 transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)]"
          >
            Dashboard
          </Link>
        </nav>

        {/* Header */}
        <header className="mt-8 border-b border-[var(--qt-border)] pb-8">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--qt-text-muted)]">
            Audit Trail
          </p>
          <h1 className="qt-display-heading mt-2 text-3xl text-[var(--qt-text-primary)] sm:text-4xl">
            {displayValue(case_id)}
          </h1>
          <p className="mt-3 text-sm text-[var(--qt-text-secondary)]">
            {events.length} {events.length === 1 ? "event" : "events"} recorded
          </p>
        </header>

        {/* States */}
        {loading ? <LoadingState /> : null}
        {!loading && error ? <ErrorState message={error} onRetry={loadAuditTrail} /> : null}
        {!loading && !error && events.length === 0 ? <EmptyState /> : null}

        {/* Timeline */}
        {!loading && !error && events.length > 0 ? (
          <div className="mt-10 space-y-12">
            {/* Chronological Timeline */}
            <section>
              <h2 className="text-xs font-medium uppercase tracking-wide text-[var(--qt-text-muted)]">
                Chronological Timeline
              </h2>
              {chronological_events.length > 0 ? (
                <ol className="relative mt-6 border-l border-[var(--qt-border)] pl-8">
                  {chronological_events.map(({ event, index }) => (
                    <AuditEventItem key={event.event_id || index} event={event} />
                  ))}
                </ol>
              ) : (
                <p className="mt-4 text-sm text-[var(--qt-text-muted)]">
                  No events with valid timestamps were returned.
                </p>
              )}
            </section>

            {/* Unordered Events */}
            {unordered_events.length > 0 ? (
              <section>
                <h2 className="text-xs font-medium uppercase tracking-wide text-[var(--qt-text-muted)]">
                  Unordered Events
                </h2>
                <p className="mt-2 text-sm text-[var(--qt-text-secondary)]">
                  Timestamp data is missing or invalid for these events.
                </p>
                <ol className="relative mt-6 border-l border-[var(--qt-border)] pl-8">
                  {unordered_events.map(({ event, index }) => (
                    <AuditEventItem key={event.event_id || `unordered-${index}`} event={event} />
                  ))}
                </ol>
              </section>
            ) : null}
          </div>
        ) : null}
      </div>
    </main>
  );
}

function AuditEventItem({ event }) {
  const tone = getEventTone(event);
  const heading = getEventLabel(event);
  const details_value = renderStructuredValue(event.details);
  const payload_value = renderStructuredValue(event.payload);
  const actor = getActorLabel(event);

  return (
    <li className="relative pb-10 last:pb-0">
      {/* Timeline marker */}
      <span className={`absolute -left-[33px] top-1 h-2.5 w-2.5 rounded-full ${tone.marker_color}`} />

      <article>
        {/* Timestamp */}
        <time className="text-xs text-[var(--qt-text-muted)]">
          {event.timestamp ? formatDateTime(event.timestamp) : "Timestamp not provided"}
        </time>

        {/* Event header */}
        <div className="mt-2 flex flex-wrap items-start gap-3">
          <h3 className="text-base font-medium text-[var(--qt-text-primary)]">
            {heading}
          </h3>
          <span className={`qt-badge ${tone.badge_class}`}>
            {tone.label}
          </span>
        </div>

        {/* Actor and stage */}
        {(actor || event.stage) ? (
          <p className="mt-2 text-sm text-[var(--qt-text-secondary)]">
            {actor ? <span>{actor}</span> : null}
            {actor && event.stage ? <span className="mx-1.5 text-[var(--qt-text-muted)]">·</span> : null}
            {event.stage ? <span>Stage: {event.stage}</span> : null}
          </p>
        ) : null}

        {/* Summary */}
        {event.summary ? (
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--qt-text-secondary)]">
            {event.summary}
          </p>
        ) : null}

        {/* Override reason - prominent display */}
        {event.override_reason ? (
          <div className="mt-4 border-l-[3px] border-l-[var(--qt-critical)] bg-red-50 py-3 pl-4 pr-3">
            <p className="text-xs font-medium uppercase tracking-wide text-red-700">
              Override Reason
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-red-800">
              {event.override_reason}
            </p>
          </div>
        ) : null}

        {/* Expandable details and payload */}
        {(details_value !== null || payload_value !== null) ? (
          <div className="mt-4 space-y-2">
            {details_value !== null ? (
              <DisclosureBlock label="Details" value={details_value} />
            ) : null}
            {payload_value !== null ? (
              <DisclosureBlock label="Payload" value={payload_value} />
            ) : null}
          </div>
        ) : null}
      </article>
    </li>
  );
}

function DisclosureBlock({ label, value }) {
  return (
    <details className="group border border-[var(--qt-border)] bg-[var(--qt-surface)]">
      <summary className="cursor-pointer px-4 py-2.5 text-xs font-medium text-[var(--qt-text-secondary)] outline-none transition-colors hover:text-[var(--qt-text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-inset">
        {label}
        <span className="ml-1 text-[var(--qt-text-muted)] group-open:hidden">+</span>
        <span className="ml-1 hidden text-[var(--qt-text-muted)] group-open:inline">−</span>
      </summary>
      <pre className="max-h-64 overflow-auto border-t border-[var(--qt-border)] bg-[var(--qt-bg)] px-4 py-3 text-xs leading-relaxed text-[var(--qt-text-secondary)]">
        {value}
      </pre>
    </details>
  );
}

function LoadingState() {
  return (
    <div className="mt-10 border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6 text-sm text-[var(--qt-text-secondary)]">
      Loading audit trail...
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="mt-10 border border-[var(--qt-border)] border-l-[3px] border-l-[var(--qt-critical)] bg-[var(--qt-surface)] p-6">
      <p className="text-sm text-[var(--qt-text-primary)]">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="qt-action-primary mt-4 bg-[var(--qt-text-primary)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--qt-text-secondary)]"
      >
        Retry
      </button>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mt-10 border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6 text-sm text-[var(--qt-text-muted)]">
      No audit events were returned.
    </div>
  );
}