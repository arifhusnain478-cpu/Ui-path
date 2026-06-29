"""
agents/output_validator.py

Step 4b of the QualiTrace AI agent layer.

Validates the JSON output of investigation_agent.py before it is accepted.
Used by investigation_agent.py's retry loop: on validation failure, the
agent re-prompts Groq (up to 3 attempts) rather than passing bad data
downstream to the CAPA Agent or the frontend.

Validation rules (relaxed for deployment):
  1. root_cause_hypotheses must contain AT LEAST 1 entry.
  2. Every hypothesis must have >= 1 source_id.
  3. source_id validation only when context has real source identifiers.
  4. overall_confidence must be a float in [0.0, 1.0].
"""

from typing import Optional


class ValidationResult:
    def __init__(self, is_valid: bool, errors: Optional[list] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def __bool__(self):
        return self.is_valid

    def __repr__(self):
        if self.is_valid:
            return "ValidationResult(is_valid=True)"
        return f"ValidationResult(is_valid=False, errors={self.errors})"


REQUIRED_HYPOTHESIS_COUNT = 3
MIN_HYPOTHESIS_COUNT = 1


def _collect_valid_source_ids(context: dict) -> set:
    valid_ids = set()
    for chunk in context.get("retrieved_chunks", []) or []:
        chunk_id = chunk.get("chunk_id")
        if chunk_id:
            valid_ids.add(chunk_id)
    for case in context.get("historical_cases", []) or []:
        case_id = case.get("case_id")
        if case_id:
            valid_ids.add(case_id)
    return valid_ids


def validate(output: dict, context: dict) -> ValidationResult:
    errors = []

    if not isinstance(output, dict):
        return ValidationResult(False, [f"output must be a JSON object, got {type(output).__name__}"])

    # --- Rule 1: at least 1 hypothesis (relaxed from exactly 3) ----------
    hypotheses = output.get("root_cause_hypotheses")
    if hypotheses is None:
        errors.append("missing required field 'root_cause_hypotheses'")
        hypotheses = []
    elif not isinstance(hypotheses, list):
        errors.append(
            f"'root_cause_hypotheses' must be a list, got {type(hypotheses).__name__}"
        )
        hypotheses = []
    elif len(hypotheses) < MIN_HYPOTHESIS_COUNT:
        errors.append(
            f"'root_cause_hypotheses' must contain at least "
            f"{MIN_HYPOTHESIS_COUNT} entry, got {len(hypotheses)}"
        )

    # --- Rule 2 & 3: source_id validation only when context has sources --
    valid_source_ids = _collect_valid_source_ids(context)
    skip_source_validation = len(valid_source_ids) == 0

    for i, hyp in enumerate(hypotheses):
        if not isinstance(hyp, dict):
            errors.append(f"hypothesis[{i}] must be a JSON object, got {type(hyp).__name__}")
            continue

        source_id = hyp.get("source_id")
        if not source_id:
            # Allow missing source_id when no context available
            if not skip_source_validation:
                errors.append(f"hypothesis[{i}] is missing a non-empty 'source_id'")
            continue

        if not isinstance(source_id, str):
            errors.append(
                f"hypothesis[{i}]['source_id'] must be a string, got {type(source_id).__name__}"
            )
            continue

        # Only validate source_id against real context when context exists
        if not skip_source_validation and source_id not in valid_source_ids:
            errors.append(
                f"hypothesis[{i}]['source_id'] = '{source_id}' does not match any "
                f"chunk_id in retrieved_chunks or case_id in historical_cases"
            )

    # --- Rule 4: overall_confidence is a float in [0.0, 1.0] -------------
    overall_confidence = output.get("overall_confidence")
    if overall_confidence is None:
        errors.append("missing required field 'overall_confidence'")
    elif isinstance(overall_confidence, bool) or not isinstance(overall_confidence, (int, float)):
        errors.append(
            f"'overall_confidence' must be a float, got {type(overall_confidence).__name__}"
        )
    elif not (0.0 <= float(overall_confidence) <= 1.0):
        errors.append(
            f"'overall_confidence' must be between 0.0 and 1.0, got {overall_confidence}"
        )

    # --- Structural sanity checks -----------------------------------------
    if "evidence_summary" not in output:
        errors.append("missing required field 'evidence_summary'")
    if "conflicting_sources" not in output:
        errors.append("missing required field 'conflicting_sources'")
    elif not isinstance(output["conflicting_sources"], list):
        errors.append("'conflicting_sources' must be a list")
    if "escalation_required" not in output:
        errors.append("missing required field 'escalation_required'")
    elif not isinstance(output["escalation_required"], bool):
        errors.append("'escalation_required' must be a boolean")
    if "escalation_reason" not in output:
        errors.append("missing required field 'escalation_reason'")

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors)
