import { CONFIDENCE_THRESHOLDS } from "../config/constants.js";

function getDisplayValue(confidence_score) {
  if (typeof confidence_score !== "number" || Number.isNaN(confidence_score)) {
    return null;
  }

  return Math.min(1, Math.max(0, confidence_score));
}

export default function ConfidenceBadge({ confidence_score, label = "Confidence" }) {
  const display_value = getDisplayValue(confidence_score);

  if (display_value === null) {
    return (
      <div className="border border-[var(--qt-border)] bg-[var(--qt-bg)] px-4 py-3">
        <p className="text-sm text-[var(--qt-text-muted)]">{label}: Not available</p>
      </div>
    );
  }

  const percent = Math.round(display_value * 100);
  const is_low_confidence = display_value < CONFIDENCE_THRESHOLDS.low;

  const border_color =
    display_value > CONFIDENCE_THRESHOLDS.high
      ? "border-l-[var(--qt-success)]"
      : display_value >= CONFIDENCE_THRESHOLDS.warning
        ? "border-l-[var(--qt-warning)]"
        : "border-l-[var(--qt-critical)]";

  const text_color =
    display_value > CONFIDENCE_THRESHOLDS.high
      ? "text-emerald-700"
      : display_value >= CONFIDENCE_THRESHOLDS.warning
        ? "text-amber-700"
        : "text-red-700";

  const bar_color =
    display_value > CONFIDENCE_THRESHOLDS.high
      ? "bg-emerald-500"
      : display_value >= CONFIDENCE_THRESHOLDS.warning
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className={`border border-[var(--qt-border)] border-l-[3px] bg-[var(--qt-surface)] px-4 py-3 ${border_color}`}>
      <div className="flex items-center justify-between gap-4">
        <span className="text-xs text-[var(--qt-text-muted)]">
          {is_low_confidence ? `Low ${label.toLowerCase()}` : label}
        </span>
        <span className={`text-lg font-medium ${text_color}`}>{percent}%</span>
      </div>
      <div className="mt-2 h-1 overflow-hidden bg-[var(--qt-bg)]">
        <div
          className={`h-full ${bar_color}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}