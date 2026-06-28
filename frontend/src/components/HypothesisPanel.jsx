import ConfidenceBadge from "./ConfidenceBadge.jsx";

function isValidRank(rank) {
  return typeof rank === "number" && Number.isFinite(rank);
}

// Maps investigation agent's likelihood string to a float for ConfidenceBadge
const LIKELIHOOD_TO_SCORE = {
  high: 0.85,
  medium: 0.55,
  low: 0.25,
};

function resolveConfidence(hypothesis) {
  // Use confidence float directly if available
  if (typeof hypothesis?.confidence === "number" && !Number.isNaN(hypothesis.confidence)) {
    return hypothesis.confidence;
  }
  // Fall back to mapping likelihood string → float
  if (typeof hypothesis?.likelihood === "string") {
    return LIKELIHOOD_TO_SCORE[hypothesis.likelihood.toLowerCase()] ?? null;
  }
  return null;
}

function getHypotheses(investigation_output) {
  const hypotheses = investigation_output?.root_cause_hypotheses;

  if (!Array.isArray(hypotheses)) {
    return [];
  }

  return [...hypotheses].sort((a, b) => {
    if (isValidRank(a?.rank) && isValidRank(b?.rank)) {
      return a.rank - b.rank;
    }
    return 0;
  });
}

export default function HypothesisPanel({ investigation_output }) {
  const hypotheses = getHypotheses(investigation_output);

  if (!investigation_output || Object.keys(investigation_output).length === 0 || hypotheses.length === 0) {
    return null;
  }

  return (
    <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
      <h2 className="qt-section-heading">Root Cause Hypotheses</h2>
      <div className="mt-5 space-y-4">
        {hypotheses.map((hypothesis, index) => (
          <article
            key={`${hypothesis?.rank ?? index}-${hypothesis?.hypothesis ?? "hypothesis"}`}
            className={`border p-4 ${
              index === 0
                ? "border-l-[3px] border-l-blue-400 bg-blue-50"
                : "border-[var(--qt-border)] bg-[var(--qt-bg)]"
            }`}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-[var(--qt-text-muted)]">
                  Rank {hypothesis?.rank ?? "—"}
                </p>
                <h3 className="mt-1 text-sm font-medium text-[var(--qt-text-primary)]">
                  {hypothesis?.hypothesis || "Hypothesis text not provided"}
                </h3>
                {/* Show likelihood label if present */}
                {hypothesis?.likelihood && (
                  <p className="mt-1 text-xs text-[var(--qt-text-muted)] capitalize">
                    Likelihood: {hypothesis.likelihood}
                  </p>
                )}
              </div>
              <div className="w-full sm:w-40">
                <ConfidenceBadge confidence_score={resolveConfidence(hypothesis)} />
              </div>
            </div>
            {hypothesis?.supporting_evidence ? (
              <p className="qt-copy mt-3 text-sm">
                {hypothesis.supporting_evidence}
              </p>
            ) : null}
            {Array.isArray(hypothesis?.source_ids) && hypothesis.source_ids.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {hypothesis.source_ids.map((source_id) => (
                  <span
                    key={source_id}
                    className="qt-badge border-[var(--qt-border)] bg-[var(--qt-surface)] text-[var(--qt-text-secondary)]"
                  >
                    {source_id}
                  </span>
                ))}
              </div>
            ) : null}
            {/* Fallback: show source_id from investigation agent format */}
            {hypothesis?.source_id && !Array.isArray(hypothesis?.source_ids) ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                <span className="qt-badge border-[var(--qt-border)] bg-[var(--qt-surface)] text-[var(--qt-text-secondary)]">
                  {hypothesis.source_id}
                </span>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
