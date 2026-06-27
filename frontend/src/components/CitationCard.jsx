import { useState } from "react";
import { displayValue } from "../utils/display.js";

export default function CitationCard({ citation }) {
  const [expanded, setExpanded] = useState(false);

  if (typeof citation === "string") {
    return (
      <div className="border border-[var(--qt-border)] bg-[var(--qt-bg)] px-4 py-3 text-sm text-[var(--qt-text-secondary)]">
        {citation}
      </div>
    );
  }

  if (!citation || typeof citation !== "object") {
    return (
      <div className="border border-[var(--qt-border)] bg-[var(--qt-bg)] px-4 py-3 text-sm text-[var(--qt-text-muted)]">
        Citation is not available.
      </div>
    );
  }

  const fields = [
    ["Source", citation.source],
    ["Section", citation.section],
    ["Authority", citation.authority],
    ["Document type", citation.doc_type],
    ["Relevance", citation.relevance_score],
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");

  return (
    <article className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-4">
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        {fields.length > 0 ? (
          fields.map(([label, value]) => (
            <div key={label} className={label === "Source" ? "sm:col-span-2" : ""}>
              <dt className="text-xs text-[var(--qt-text-muted)]">{label}</dt>
              <dd className="mt-0.5 break-words text-[var(--qt-text-primary)]">{displayValue(value)}</dd>
            </div>
          ))
        ) : (
          <div>
            <dt className="text-xs text-[var(--qt-text-muted)]">Citation</dt>
            <dd className="mt-0.5 text-[var(--qt-text-muted)]">Metadata not provided.</dd>
          </div>
        )}
      </dl>

      {citation.text ? (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="text-xs text-[var(--qt-text-muted)] underline underline-offset-2 transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)]"
          >
            {expanded ? "Hide text" : "Show text"}
          </button>
          {expanded ? (
            <p className="mt-3 max-h-60 overflow-auto whitespace-pre-wrap break-words border-l-2 border-[var(--qt-border)] bg-[var(--qt-bg)] py-2 pl-4 pr-3 text-sm leading-relaxed text-[var(--qt-text-secondary)]">
              {citation.text}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}