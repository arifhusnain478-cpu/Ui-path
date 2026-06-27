"""
agents/output_validator.py

Step 4b of the QualiTrace AI agent layer.

Validates the JSON output of investigation_agent.py before it is accepted.
Used by investigation_agent.py's retry loop: on validation failure, the
agent re-prompts Groq (up to 3 attempts) rather than passing bad data
downstream to the CAPA Agent or the frontend.

Validation rules (from the handoff spec):
  1. root_cause_hypotheses must contain EXACTLY 3 entries.
  2. Every hypothesis must have >= 1 source_id.
  3. Every source_id must exist in the context's real source identifiers.
  4. overall_confidence must be a float in [0.0, 1.0].

Note on rule 3 — "exists in the context source_list":
context_builder.py's source_list is a list of formatted display strings,
e.g. "fda_21cfr_211 — Section 3" (filename + section), not raw chunk_ids.
The Investigation Agent prompt (prompts.py) asks the model to cite a
source_id matching a chunk_id from retrieved_chunks or a case_id from
historical_cases. A source_id like "fda_21cfr_211_chunk_0001" can never
string-match a source_list entry like "fda_21cfr_211 — Section 3" — those
are different identifier spaces entirely.

So this validator checks source_id membership against the actual
identifiers present in the context: the chunk_ids in
context["retrieved_chunks"] and the case_ids in context["historical_cases"].
This is the only check that can succeed and still actually catch
fabricated citations, which is the real intent of the rule.
"""

from typing import Optional


class ValidationResult:
    """
    Simple result object returned by validate().

    Attributes:
        is_valid: True if the output passed all checks.
        errors: list of human-readable error strings. Empty if is_valid.
    """

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


def _collect_valid_source_ids(context: dict) -> set:
    """
    Builds the set of legitimate source identifiers from a RAG context
    object (the shape produced by rag/context_builder.py): every chunk_id
    in retrieved_chunks, plus every case_id in historical_cases.
    """
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
    """
    Validates an Investigation Agent JSON output against the RAG context
    it was generated from.

    Args:
        output: the parsed JSON dict returned by the Investigation Agent.
            Expected shape (see prompts.INVESTIGATION_SYSTEM_PROMPT):
            {
              "evidence_summary": str,
              "root_cause_hypotheses": [
                  {"hypothesis": str, "source_id": str, "likelihood": str}, ...
              ],
              "overall_confidence": float,
              "conflicting_sources": [...],
              "escalation_required": bool,
              "escalation_reason": str
            }
        context: the RAG context dict the agent was given (the output of
            rag/context_builder.py), used to check source_id legitimacy.

    Returns:
        ValidationResult. Collects ALL errors found (does not short-circuit
        on the first failure) so a single retry prompt can tell the model
        everything wrong with its previous attempt at once.
    """
    errors = []

    if not isinstance(output, dict):
        return ValidationResult(False, [f"output must be a JSON object, got {type(output).__name__}"])

    # --- Rule 1: exactly 3 hypotheses -------------------------------------
    hypotheses = output.get("root_cause_hypotheses")
    if hypotheses is None:
        errors.append("missing required field 'root_cause_hypotheses'")
        hypotheses = []
    elif not isinstance(hypotheses, list):
        errors.append(
            f"'root_cause_hypotheses' must be a list, got {type(hypotheses).__name__}"
        )
        hypotheses = []
    elif len(hypotheses) != REQUIRED_HYPOTHESIS_COUNT:
        errors.append(
            f"'root_cause_hypotheses' must contain exactly "
            f"{REQUIRED_HYPOTHESIS_COUNT} entries, got {len(hypotheses)}"
        )

    # --- Rule 2 & 3: every hypothesis has >=1 source_id, and it's real ---
    valid_source_ids = _collect_valid_source_ids(context)

    for i, hyp in enumerate(hypotheses):
        if not isinstance(hyp, dict):
            errors.append(f"hypothesis[{i}] must be a JSON object, got {type(hyp).__name__}")
            continue

        source_id = hyp.get("source_id")
        if not source_id:
            errors.append(f"hypothesis[{i}] is missing a non-empty 'source_id'")
            continue

        if not isinstance(source_id, str):
            errors.append(
                f"hypothesis[{i}]['source_id'] must be a string, got {type(source_id).__name__}"
            )
            continue

        if source_id not in valid_source_ids:
            errors.append(
                f"hypothesis[{i}]['source_id'] = '{source_id}' does not match any "
                f"chunk_id in retrieved_chunks or case_id in historical_cases "
                f"(fabricated or hallucinated citation)"
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

    # --- Structural sanity checks on the remaining required fields -------
    # Not explicitly in the 4 numbered rules, but required by the Investigation
    # Agent's documented output contract (prompts.py / handoff spec) — checked
    # here too so a malformed-but-technically-passing-the-4-rules output still
    # gets caught and retried rather than breaking output_validator's callers.
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


if __name__ == "__main__":
    # Smoke test matching the handoff spec:
    # "valid investigation JSON passes, JSON missing source_ids fails"
    mock_context = {
        "retrieved_chunks": [
            {"chunk_id": "fda_21cfr_211_chunk_0001", "source": "fda_21cfr_211",
             "doc_type": "REGULATION", "section": "3", "text": "...", "relevance_score": 0.82},
            {"chunk_id": "sop_qa_042_site_a_chunk_0000", "source": "sop_qa_042_site_a",
             "doc_type": "SOP", "section": "1", "text": "...", "relevance_score": 0.75},
        ],
        "historical_cases": [
            {"case_id": "CASE-2023-0451", "similarity_score": 0.88,
             "outcome": "effective", "root_cause": "Packaging seal failure"},
        ],
        "source_list": ["fda_21cfr_211 — Section 3", "sop_qa_042_site_a — Section 1"],
    }

    valid_output = {
        "evidence_summary": "Evidence points to a packaging seal failure.",
        "root_cause_hypotheses": [
            {"hypothesis": "Seal integrity failure during packaging",
             "source_id": "sop_qa_042_site_a_chunk_0000", "likelihood": "high"},
            {"hypothesis": "Similar root cause as prior packaging case",
             "source_id": "CASE-2023-0451", "likelihood": "medium"},
            {"hypothesis": "Possible deviation from CGMP complaint handling",
             "source_id": "fda_21cfr_211_chunk_0001", "likelihood": "low"},
        ],
        "overall_confidence": 0.78,
        "conflicting_sources": [],
        "escalation_required": False,
        "escalation_reason": "",
    }

    result = validate(valid_output, mock_context)
    assert result.is_valid, f"Expected valid output to pass, got errors: {result.errors}"
    print("PASS: valid investigation JSON passes validation")

    # Missing source_id case
    invalid_output_missing_source = {
        "evidence_summary": "Evidence points to a packaging seal failure.",
        "root_cause_hypotheses": [
            {"hypothesis": "Seal integrity failure during packaging",
             "source_id": "", "likelihood": "high"},
            {"hypothesis": "Similar root cause as prior packaging case",
             "source_id": "CASE-2023-0451", "likelihood": "medium"},
            {"hypothesis": "Possible deviation from CGMP complaint handling",
             "source_id": "fda_21cfr_211_chunk_0001", "likelihood": "low"},
        ],
        "overall_confidence": 0.78,
        "conflicting_sources": [],
        "escalation_required": False,
        "escalation_reason": "",
    }
    result = validate(invalid_output_missing_source, mock_context)
    assert not result.is_valid, "Expected missing source_id to fail validation"
    assert any("source_id" in e for e in result.errors)
    print(f"PASS: missing source_id correctly fails -> {result.errors}")

    # Fabricated source_id case
    invalid_output_fake_source = dict(valid_output)
    invalid_output_fake_source["root_cause_hypotheses"] = [
        {"hypothesis": "Made up cause", "source_id": "totally_fake_chunk_9999", "likelihood": "high"},
        {"hypothesis": "Similar root cause as prior packaging case",
         "source_id": "CASE-2023-0451", "likelihood": "medium"},
        {"hypothesis": "Possible deviation from CGMP complaint handling",
         "source_id": "fda_21cfr_211_chunk_0001", "likelihood": "low"},
    ]
    result = validate(invalid_output_fake_source, mock_context)
    assert not result.is_valid, "Expected fabricated source_id to fail validation"
    print(f"PASS: fabricated source_id correctly fails -> {result.errors}")

    # Wrong hypothesis count
    invalid_output_wrong_count = dict(valid_output)
    invalid_output_wrong_count["root_cause_hypotheses"] = valid_output["root_cause_hypotheses"][:2]
    result = validate(invalid_output_wrong_count, mock_context)
    assert not result.is_valid, "Expected wrong hypothesis count to fail validation"
    print(f"PASS: wrong hypothesis count correctly fails -> {result.errors}")

    # Out-of-range confidence
    invalid_output_bad_confidence = dict(valid_output)
    invalid_output_bad_confidence["overall_confidence"] = 1.4
    result = validate(invalid_output_bad_confidence, mock_context)
    assert not result.is_valid, "Expected out-of-range confidence to fail validation"
    print(f"PASS: out-of-range confidence correctly fails -> {result.errors}")

    print("\nAll output_validator smoke tests passed.")
