import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createComplaint } from "../api/cases.js";
import {
  APP_ROUTES,
  COMPLAINT_TYPES,
  JURISDICTIONS,
} from "../config/constants.js";

const initial_form = {
  product_name: "",
  batch_number: "",
  market_code: "US",
  complaint_type: "quality",
  patient_impact: false,
  description: "",
};

export default function NewComplaint() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initial_form);
  const [field_errors, setFieldErrors] = useState({});
  const [submit_error, setSubmitError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateField(event) {
    const { name, type, checked, value } = event.target;
    setForm((current_form) => ({
      ...current_form,
      [name]: type === "checkbox" ? checked : value,
    }));

    setFieldErrors((current_errors) => ({
      ...current_errors,
      [name]: "",
    }));
  }

  function validateForm() {
    const errors = {};

    if (!form.product_name.trim()) {
      errors.product_name = "Product name is required.";
    }

    if (!JURISDICTIONS.includes(form.market_code)) {
      errors.market_code = "Select US or EU.";
    }

    if (!COMPLAINT_TYPES.includes(form.complaint_type)) {
      errors.complaint_type = "Select an approved complaint type.";
    }

    if (!form.description.trim()) {
      errors.description = "Description is required.";
    }

    return errors;
  }

  function buildPayload() {
    const trimmed_batch_number = form.batch_number.trim();

    return {
      product_name: form.product_name.trim(),
      batch_number:
        trimmed_batch_number.length > 0 ? trimmed_batch_number : null,
      market_code: form.market_code,
      complaint_type: form.complaint_type,
      patient_impact: Boolean(form.patient_impact),
      description: form.description.trim(),
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (loading) {
      return;
    }

    setSubmitError("");
    const errors = validateForm();
    setFieldErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    setLoading(true);

    try {
      const created_case = await createComplaint(buildPayload());
      navigate(APP_ROUTES.case_detail(created_case.case_id));
    } catch (error) {
      setSubmitError(
        error?.message || "Complaint could not be submitted. Please try again.",
      );
      setLoading(false);
    }
  }

  return (
    <main className="qt-page">
      <div className="qt-container">
        <div className="grid gap-10 lg:grid-cols-[0.4fr_0.6fr]">
          {/* Left: Context */}
          <aside className="lg:sticky lg:top-20 lg:self-start">
            <p className="qt-eyebrow">Complaint intake</p>
            <h1 className="qt-page-heading mt-3">New Complaint</h1>
            <p className="qt-copy mt-4 text-sm">
              Submit complaint details for triage and case creation. Batch
              information is optional but may delay processing if missing.
            </p>
            <div className="mt-6 h-px bg-[var(--qt-border)]" />
            <dl className="mt-6 space-y-4 text-sm">
              <div>
                <dt className="text-xs text-[var(--qt-text-muted)]">Market codes</dt>
                <dd className="mt-1 text-[var(--qt-text-secondary)]">US, EU</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--qt-text-muted)]">Complaint types</dt>
                <dd className="mt-1 text-[var(--qt-text-secondary)]">Contamination, Labeling, Quality</dd>
              </div>
            </dl>
          </aside>

          {/* Right: Form */}
          <form
            className="border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6 sm:p-8"
            onSubmit={handleSubmit}
            noValidate
          >
            <div className="space-y-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <TextField
                  label="Product name"
                  name="product_name"
                  value={form.product_name}
                  error={field_errors.product_name}
                  onChange={updateField}
                  required
                />

                <TextField
                  label="Batch number"
                  name="batch_number"
                  value={form.batch_number}
                  error={field_errors.batch_number}
                  onChange={updateField}
                  optional
                />
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <SelectField
                  label="Market code"
                  name="market_code"
                  value={form.market_code}
                  options={JURISDICTIONS}
                  error={field_errors.market_code}
                  onChange={updateField}
                  required
                />

                <SelectField
                  label="Complaint type"
                  name="complaint_type"
                  value={form.complaint_type}
                  options={COMPLAINT_TYPES}
                  error={field_errors.complaint_type}
                  onChange={updateField}
                  required
                />
              </div>

              <div>
                <label className="flex cursor-pointer items-start gap-3 border border-[var(--qt-border)] bg-[var(--qt-bg)] p-4 text-sm">
                  <input
                    type="checkbox"
                    name="patient_impact"
                    checked={form.patient_impact}
                    onChange={updateField}
                    disabled={loading}
                    className="mt-0.5 h-4 w-4 border-[var(--qt-border)] text-[var(--qt-text-primary)] focus:ring-[var(--qt-text-primary)] focus:ring-offset-0"
                  />
                  <span>
                    <span className="block font-medium text-[var(--qt-text-primary)]">
                      Patient impact
                    </span>
                    <span className="mt-0.5 block text-[var(--qt-text-secondary)]">
                      Check if the complaint involves patient impact.
                    </span>
                  </span>
                </label>
              </div>

              <TextAreaField
                label="Description"
                name="description"
                value={form.description}
                error={field_errors.description}
                onChange={updateField}
                required
              />
            </div>

            {submit_error ? (
              <div
                role="alert"
                className="mt-6 border-l-2 border-[var(--qt-critical)] bg-red-50 px-4 py-3 text-sm text-red-800"
              >
                {submit_error}
              </div>
            ) : null}

            <div className="mt-8 flex flex-col-reverse gap-3 border-t border-[var(--qt-border)] pt-6 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => navigate(APP_ROUTES.dashboard)}
                disabled={loading}
                className="qt-action-secondary px-5 py-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                aria-busy={loading}
                className="qt-action-primary px-5 py-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Submitting..." : "Submit Complaint"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
}

function TextField({
  label,
  name,
  value,
  error,
  onChange,
  required = false,
  optional = false,
}) {
  const error_id = `${name}_error`;

  return (
    <div>
      <label htmlFor={name} className="qt-label">
        {label}
        {optional ? (
          <span className="ml-1.5 font-normal text-[var(--qt-text-muted)]">Optional</span>
        ) : null}
      </label>
      <input
        id={name}
        name={name}
        type="text"
        value={value}
        onChange={onChange}
        required={required}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? error_id : undefined}
        className="qt-field mt-1.5 block px-3 py-2.5 text-sm"
      />
      {error ? (
        <p id={error_id} className="mt-1.5 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function SelectField({ label, name, value, options, error, onChange, required }) {
  const error_id = `${name}_error`;

  return (
    <div>
      <label htmlFor={name} className="qt-label">
        {label}
      </label>
      <select
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        required={required}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? error_id : undefined}
        className="qt-field mt-1.5 block px-3 py-2.5 text-sm"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      {error ? (
        <p id={error_id} className="mt-1.5 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function TextAreaField({ label, name, value, error, onChange, required }) {
  const error_id = `${name}_error`;

  return (
    <div>
      <label htmlFor={name} className="qt-label">
        {label}
      </label>
      <textarea
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        required={required}
        rows={5}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? error_id : undefined}
        className="qt-field mt-1.5 block resize-y px-3 py-2.5 text-sm"
      />
      {error ? (
        <p id={error_id} className="mt-1.5 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}