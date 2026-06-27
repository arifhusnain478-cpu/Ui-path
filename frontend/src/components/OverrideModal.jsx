import { useEffect, useRef } from "react";
import { MIN_OVERRIDE_REASON_LENGTH } from "../config/constants.js";

export default function OverrideModal({
  open,
  title = "Override Decision",
  reason,
  error,
  loading,
  onReasonChange,
  onCancel,
  onSubmit,
}) {
  const textareaRef = useRef(null);
  const trimmed_length = reason.trim().length;
  const is_valid = trimmed_length >= MIN_OVERRIDE_REASON_LENGTH;

  useEffect(() => {
    if (open) {
      textareaRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape" && !loading) {
        onCancel();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [loading, onCancel, open]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--qt-text-primary)]/40 px-4 py-6"
      role="presentation"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="override_modal_title"
        className="w-full max-w-lg border border-[var(--qt-border)] bg-[var(--qt-surface)] p-6"
      >
        <h2 id="override_modal_title" className="text-lg font-medium text-[var(--qt-text-primary)]">
          {title}
        </h2>
        <p className="mt-2 text-sm text-[var(--qt-text-secondary)]">
          Provide a reviewer reason using the approved override_reason field.
        </p>

        <div className="mt-5">
          <label
            htmlFor="override_reason"
            className="block text-xs font-medium text-[var(--qt-text-muted)]"
          >
            Override reason
          </label>
          <textarea
            ref={textareaRef}
            id="override_reason"
            value={reason}
            onChange={(event) => onReasonChange(event.target.value)}
            rows={5}
            disabled={loading}
            aria-invalid={Boolean(error) || (!is_valid && trimmed_length > 0)}
            aria-describedby="override_reason_help override_reason_count override_reason_error"
            className="mt-2 block w-full resize-y border border-[var(--qt-border)] bg-[var(--qt-bg)] px-3 py-2 text-sm text-[var(--qt-text-primary)] outline-none transition-colors focus:border-[var(--qt-text-secondary)] disabled:cursor-not-allowed disabled:opacity-60"
          />
          <div className="mt-2 flex items-center justify-between text-xs text-[var(--qt-text-muted)]">
            <span id="override_reason_help">Minimum {MIN_OVERRIDE_REASON_LENGTH} characters</span>
            <span id="override_reason_count">{trimmed_length}</span>
          </div>
          {error ? (
            <p id="override_reason_error" className="mt-2 text-sm text-[var(--qt-critical)]">
              {error}
            </p>
          ) : null}
        </div>

        <div className="mt-6 flex flex-col-reverse gap-3 border-t border-[var(--qt-border)] pt-5 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="qt-action-secondary px-4 py-2 text-sm transition-colors hover:bg-[var(--qt-bg)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={!is_valid || loading}
            className="qt-action-primary bg-[var(--qt-text-primary)] px-4 py-2 text-sm text-white transition-colors hover:bg-[var(--qt-text-secondary)] disabled:cursor-not-allowed disabled:bg-[var(--qt-text-muted)]"
          >
            {loading ? "Submitting..." : "Submit Override"}
          </button>
        </div>
      </section>
    </div>
  );
}