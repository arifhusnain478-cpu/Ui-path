import ConfidenceBadge from "./ConfidenceBadge.jsx";

function isValidRank(rank) {
  return typeof rank === "number" && Number.isFinite(rank);
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

  if (hypotheses.length === 0) {
    return (
      <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
        <h2 className="qt-section-heading">Root Cause Hypotheses</h2>
        <p className="mt-4 text-sm text-[var(--qt-text-muted)]">No hypotheses were returned.</p>
      </section>
    );
  }

  return (
    <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
      <h2 className="qt-section-heading">Root Cause Hypotheses</h2>
      <div className="mt-5 space-y-4">
        {hypotheses.map((hypothesis, index) => (
          <article
            key={`${hypothesis?.rank ?? index}-${hypothesis?.hypothesis ?? "hypothesis"}`}
            className={`border p-4 ${
              index === 0 ? "border-l-[3px] border-l-blue-400 bg-blue-50" : "border-[var(--qt-border)] bg-[var(--qt-bg)]"
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
              </div>
              <div className="w-full sm:w-40">
                <ConfidenceBadge confidence_score={hypothesis?.confidence} />
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
          </article>
        ))}
      </div>
    </section>
  );
}