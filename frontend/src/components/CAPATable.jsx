import {
  displayValue,
  formatDate,
  formatRoleLabel,
  formatSnakeCaseLabel,
} from "../utils/display.js";

export default function CAPATable({ capa_plan }) {
  if (!Array.isArray(capa_plan) || capa_plan.length === 0) {
    return (
      <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
        <h2 className="qt-section-heading">CAPA Plan</h2>
        <p className="mt-4 text-sm text-[var(--qt-text-muted)]">No CAPA plan was returned.</p>
      </section>
    );
  }

  return (
    <section className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6">
      <h2 className="qt-section-heading">CAPA Plan</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-[980px] w-full text-left text-sm">
          <thead className="border-b border-[var(--qt-border)]">
            <tr>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Type</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Description</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Responsible</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Due</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Status</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Evidence</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Metric</th>
              <th className="px-3 py-2 text-xs font-medium text-[var(--qt-text-muted)]">Sources</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--qt-border)]">
            {capa_plan.map((action, index) => (
              <tr key={`${action?.description ?? "capa"}-${index}`} className="align-top">
                <td className="whitespace-nowrap px-3 py-3">
                  <span
                    className={`qt-badge ${
                      action?.type === "corrective"
                        ? "border-red-200 bg-red-50 text-red-700"
                        : action?.type === "preventive"
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : "border-[var(--qt-border)] bg-[var(--qt-bg)] text-[var(--qt-text-secondary)]"
                    }`}
                  >
                    {formatSnakeCaseLabel(action?.type)}
                  </span>
                </td>
                <td className="min-w-56 px-3 py-3 text-[var(--qt-text-primary)]">
                  {displayValue(action?.description)}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-[var(--qt-text-secondary)]">{formatRoleLabel(action?.responsible_role)}</td>
                <td className="whitespace-nowrap px-3 py-3 text-[var(--qt-text-secondary)]">{formatDate(action?.due_date)}</td>
                <td className="whitespace-nowrap px-3 py-3 text-[var(--qt-text-secondary)]">{formatSnakeCaseLabel(action?.status)}</td>
                <td className="px-3 py-3 text-[var(--qt-text-secondary)]">{displayValue(action?.evidence_required)}</td>
                <td className="px-3 py-3 text-[var(--qt-text-secondary)]">{displayValue(action?.effectiveness_metric)}</td>
                <td className="min-w-48 px-3 py-3 text-[var(--qt-text-secondary)]">
                  {Array.isArray(action?.source_citations) && action.source_citations.length > 0
                    ? action.source_citations.join(", ")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}