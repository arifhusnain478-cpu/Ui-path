import { useEffect, useState } from "react";
import { formatDateTime } from "../utils/display.js";

function getRemainingMs(sla_deadline) {
  const deadline = new Date(sla_deadline).getTime();

  if (!sla_deadline || Number.isNaN(deadline)) {
    return null;
  }

  return deadline - Date.now();
}

function formatRemaining(ms) {
  const total_seconds = Math.max(0, Math.floor(Math.abs(ms) / 1000));
  const hours = String(Math.floor(total_seconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((total_seconds % 3600) / 60)).padStart(2, "0");
  const seconds = String(total_seconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

export default function SLATimer({ sla_deadline }) {
  const [remaining_ms, setRemainingMs] = useState(() => getRemainingMs(sla_deadline));

  useEffect(() => {
    setRemainingMs(getRemainingMs(sla_deadline));

    const interval_id = window.setInterval(() => {
      setRemainingMs(getRemainingMs(sla_deadline));
    }, 1000);

    return () => window.clearInterval(interval_id);
  }, [sla_deadline]);

  if (remaining_ms === null) {
    return (
      <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
        <h2 className="qt-section-heading">SLA</h2>
        <p className="mt-4 text-sm text-[var(--qt-text-muted)]">SLA deadline is not available.</p>
      </section>
    );
  }

  const breached = remaining_ms < 0;
  const approaching = remaining_ms >= 0 && remaining_ms <= 60 * 60 * 1000;

  const border_color = breached
    ? "border-l-[var(--qt-critical)]"
    : approaching
      ? "border-l-[var(--qt-warning)]"
      : "border-l-[var(--qt-success)]";

  const text_color = breached
    ? "text-red-700"
    : approaching
      ? "text-amber-700"
      : "text-emerald-700";

  return (
    <section
      className={`border border-[var(--qt-border)] border-l-[3px] bg-[var(--qt-surface)] p-6 ${border_color}`}
      aria-live="polite"
    >
      <h2 className="text-xs font-medium uppercase tracking-wider text-[var(--qt-text-muted)]">SLA</h2>
      <p className={`mt-3 text-3xl font-normal tracking-tight ${text_color}`}>
        {formatRemaining(remaining_ms)}
      </p>
      <p className={`mt-1 text-sm ${text_color}`}>
        {breached ? "Breached" : approaching ? "Approaching" : "Remaining"}
      </p>
      <p className="mt-4 text-xs text-[var(--qt-text-muted)]">
        Deadline: {formatDateTime(sla_deadline)}
      </p>
    </section>
  );
}