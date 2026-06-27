import { useEffect } from "react";
import { Link } from "react-router-dom";
import CaseCard from "../components/CaseCard.jsx";
import { HeroVisualPlaceholder } from "../components/VisualPlaceholders.jsx";
import {
  APP_ROUTES,
  CASE_STATUSES,
  JURISDICTIONS,
  RISK_LEVELS,
} from "../config/constants.js";
import { useCaseStore } from "../store/caseStore.js";
import { formatSnakeCaseLabel } from "../utils/display.js";

export default function Dashboard() {
  const cases = useCaseStore((state) => state.cases);
  const loading = useCaseStore((state) => state.loading);
  const error = useCaseStore((state) => state.error);
  const filters = useCaseStore((state) => state.filters);
  const fetchCases = useCaseStore((state) => state.fetchCases);
  const setFilters = useCaseStore((state) => state.setFilters);
  const clearFilters = useCaseStore((state) => state.clearFilters);

  useEffect(() => {
    fetchCases(filters);
  }, [fetchCases, filters]);

  function handleFilterChange(event) {
    setFilters({ [event.target.name]: event.target.value });
  }

  function handleRetry() {
    fetchCases(filters);
  }

  function handleClearFilters() {
    clearFilters();
  }

  return (
    <main className="qt-page">
      <div className="qt-container">
        {/* Editorial Hero Section */}
        <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div className="pt-4">
            <p className="qt-eyebrow">Complaint governance</p>
            <h1 className="qt-page-heading mt-4">Cases</h1>
            <p className="qt-copy mt-4 text-base">
              Review complaint cases, risk assessments, and workflow status.
              Each case tracks investigation findings, regulatory citations,
              and audit-ready decisions.
            </p>
            <div className="mt-6">
              <Link
                to={APP_ROUTES.new_complaint}
                className="qt-action-primary inline-flex px-5 py-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2"
              >
                New Complaint
              </Link>
            </div>
          </div>
          <div className="hidden lg:block">
            <HeroVisualPlaceholder />
          </div>
        </section>

        {/* Filter Strip */}
        <section
          aria-label="Case filters"
          className="mt-10 border-y border-[var(--qt-border)] py-4"
        >
          <div className="flex flex-wrap items-end gap-4">
            <FilterSelect
              label="Jurisdiction"
              name="jurisdiction"
              value={filters.jurisdiction}
              options={JURISDICTIONS}
              onChange={handleFilterChange}
            />
            <FilterSelect
              label="Status"
              name="status"
              value={filters.status}
              options={CASE_STATUSES}
              onChange={handleFilterChange}
            />
            <FilterSelect
              label="Risk"
              name="risk_level"
              value={filters.risk_level}
              options={RISK_LEVELS}
              onChange={handleFilterChange}
            />
            <button
              type="button"
              onClick={handleClearFilters}
              className="pb-0.5 text-sm text-[var(--qt-text-muted)] underline underline-offset-2 transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)]"
            >
              Clear
            </button>
          </div>
        </section>

        {/* Case List */}
        <section className="mt-8" aria-live="polite">
          {loading ? <LoadingState /> : null}

          {!loading && error ? (
            <ErrorState message={error} onRetry={handleRetry} />
          ) : null}

          {!loading && !error && cases.length === 0 ? <EmptyState /> : null}

          {!loading && !error && cases.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {cases.map((case_record, index) => (
                <CaseCard
                  key={case_record.case_id || `case-${index}`}
                  case_record={case_record}
                />
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function FilterSelect({ label, name, value, options, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={name} className="text-sm text-[var(--qt-text-muted)]">
        {label}
      </label>
      <select
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        className="border-b border-[var(--qt-border)] bg-transparent py-1 pr-6 text-sm text-[var(--qt-text-primary)] focus:border-[var(--qt-text-primary)] focus:outline-none"
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {formatSnakeCaseLabel(option)}
          </option>
        ))}
      </select>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="py-12 text-center text-sm text-[var(--qt-text-muted)]">
      Loading cases...
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="border-l-2 border-[var(--qt-critical)] bg-red-50 px-4 py-4">
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

function EmptyState() {
  return (
    <div className="py-12 text-center text-sm text-[var(--qt-text-muted)]">
      No cases match the current filters.
    </div>
  );
}