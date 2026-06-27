import { formatSnakeCaseLabel } from "../utils/display.js";

function getStageLabel(stage) {
  if (typeof stage === "string") {
    return stage;
  }

  if (stage && typeof stage === "object") {
    return stage.name || stage.stage || stage.label || "Unnamed stage";
  }

  return "Unnamed stage";
}

function getStageState(stage, current_stage) {
  if (!stage || typeof stage !== "object") {
    return "";
  }

  return stage.status || stage.state || (getStageLabel(stage) === current_stage ? "current" : "");
}

export default function StageTracker({ current_stage, stages }) {
  const ordered_stages = Array.isArray(stages) ? stages : [];

  if (ordered_stages.length > 0) {
    return (
      <div className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
        <h2 className="qt-section-heading">Stage</h2>
        <ol className="mt-5 grid gap-3 md:grid-cols-2">
          {ordered_stages.map((stage, index) => {
            const label = getStageLabel(stage);
            const state = getStageState(stage, current_stage);
            const is_current = state === "current" || label === current_stage;
            const is_completed = state === "completed" || state === "complete";

            return (
              <li
                key={`${label}-${index}`}
                className={`border p-4 ${
                  is_current
                    ? "border-blue-200 bg-blue-50"
                    : is_completed
                      ? "border-emerald-200 bg-emerald-50"
                      : "border-[var(--qt-border)] bg-[var(--qt-bg)]"
                }`}
              >
                <p className="text-sm font-medium text-[var(--qt-text-primary)]">{label}</p>
                {state ? (
                  <p className="mt-1 text-xs text-[var(--qt-text-muted)]">{formatSnakeCaseLabel(state)}</p>
                ) : null}
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  return (
    <div className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
      <h2 className="qt-section-heading">Current Stage</h2>
      {current_stage ? (
        <div className="mt-5 border-l-2 border-blue-400 bg-blue-50 py-3 pl-4 pr-4">
          <p className="text-xs text-blue-600">Current</p>
          <p className="mt-1 break-words text-lg font-medium text-blue-900">{current_stage}</p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-[var(--qt-text-muted)]">Current stage is not available.</p>
      )}
    </div>
  );
}