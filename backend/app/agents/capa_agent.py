"""
agents/capa_agent.py

Step 4e of the QualiTrace AI agent layer — the final agent.

The CAPA Agent receives an approved root cause, the full Investigation
Agent output, and the complaint's jurisdiction. It calls Groq (model:
llama-3.3-70b-versatile) with CAPA_SYSTEM_PROMPT and returns a list of
CAPA (Corrective and Preventive Action) items.

Output (on success) — a list of items, each:
    {
      "description": str,
      "type": "corrective" | "preventive",
      "responsible_role": str,
      "due_date": str (ISO date),
      "evidence_required": str,
      "effectiveness_metric": str,
      "source_citations": [chunk_id or case_id, ...]   (>= 1 entry, all real)
    }

Validation rules (this module's own validator, analogous to
output_validator.py for the Investigation Agent):
  1. Output must be a non-empty list.
  2. At least one item has type == "corrective" and at least one has
     type == "preventive".
  3. Every item has all 7 required fields, correctly typed.
  4. Every item's source_citations is a non-empty list, and every entry
     in it must be a real chunk_id/case_id that appeared in the
     investigation output's source context (the same fabricated-citation
     check used in output_validator.py for the Investigation Agent).

API key sourced from os.environ["GROQ_API_KEY"] via .env, read lazily —
same pattern as intake_agent.py and investigation_agent.py.
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv

from .prompts import CAPA_SYSTEM_PROMPT

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
VALID_TYPES = {"corrective", "preventive"}
REQUIRED_ITEM_FIELDS = {
    "description", "type", "responsible_role", "due_date",
    "evidence_required", "effectiveness_metric", "source_citations",
}


class CapaAgentError(Exception):
    """Raised when the CAPA Agent cannot produce valid output after MAX_RETRIES attempts."""


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise CapaAgentError(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(GROQ_API_KEY=your_key_here) or export it in your shell."
        )
    from groq import Groq
    return Groq(api_key=api_key)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


def _collect_valid_source_ids(investigation_output: dict, context: Optional[dict]) -> set:
    """
    Builds the set of legitimate citation identifiers a CAPA item is
    allowed to reference. Pulls from:
      - source_id values already cited in investigation_output's
        root_cause_hypotheses (these are guaranteed real, since
        output_validator.py already checked them), and
      - if the original RAG context is also passed in, every chunk_id in
        retrieved_chunks and case_id in historical_cases (the CAPA Agent
        may justifiably cite supporting evidence beyond what the
        Investigation Agent's 3 hypotheses happened to use).
    """
    valid_ids = set()

    for hyp in investigation_output.get("root_cause_hypotheses", []) or []:
        source_id = hyp.get("source_id")
        if source_id:
            valid_ids.add(source_id)

    if context:
        for chunk in context.get("retrieved_chunks", []) or []:
            chunk_id = chunk.get("chunk_id")
            if chunk_id:
                valid_ids.add(chunk_id)
        for case in context.get("historical_cases", []) or []:
            case_id = case.get("case_id")
            if case_id:
                valid_ids.add(case_id)

    return valid_ids


def _validate_capa_output(items, valid_source_ids: set) -> Optional[str]:
    """
    Validates a parsed CAPA Agent output. Returns None if valid, else a
    semicolon-joined string describing every problem found (so a single
    retry prompt can address everything at once).
    """
    errors = []

    if not isinstance(items, list) or len(items) == 0:
        return f"output must be a non-empty JSON array, got {type(items).__name__}"

    types_seen = set()

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"item[{i}] must be a JSON object, got {type(item).__name__}")
            continue

        missing = REQUIRED_ITEM_FIELDS - set(item.keys())
        if missing:
            errors.append(f"item[{i}] is missing required fields: {sorted(missing)}")
            continue

        item_type = item.get("type")
        if item_type not in VALID_TYPES:
            errors.append(
                f"item[{i}]['type'] must be one of {sorted(VALID_TYPES)}, got {item_type!r}"
            )
        else:
            types_seen.add(item_type)

        for field in ("description", "responsible_role", "due_date",
                      "evidence_required", "effectiveness_metric"):
            if not isinstance(item.get(field), str) or not item.get(field).strip():
                errors.append(f"item[{i}]['{field}'] must be a non-empty string")

        citations = item.get("source_citations")
        if not isinstance(citations, list) or len(citations) == 0:
            errors.append(f"item[{i}]['source_citations'] must be a non-empty list")
        else:
            if valid_source_ids:  # only validate citations when RAG context is available
                for citation in citations:
                    if citation not in valid_source_ids:
                        errors.append(
                            f"item[{i}]['source_citations'] contains '{citation}', which does "
                            "not match any source_id from the investigation output or RAG "
                            "context (fabricated or hallucinated citation)"
                        )

    if "corrective" not in types_seen:
        errors.append("output must include at least one item with type == 'corrective'")
    if "preventive" not in types_seen:
        errors.append("output must include at least one item with type == 'preventive'")

    return "; ".join(errors) if errors else None


def generate_capa(
    approved_root_cause: str,
    investigation_output: dict,
    jurisdiction: str,
    context: Optional[dict] = None,
    client=None,
) -> list:
    """
    Runs the CAPA Agent given an approved root cause.

    Args:
        approved_root_cause: free-text root cause string a human reviewer
            has approved (may be one of the Investigation Agent's
            hypotheses, or an edited version of one).
        investigation_output: the full validated output of
            investigation_agent.investigate() for this case.
        jurisdiction: "US" or "EU".
        context: optional original RAG context dict (output of
            rag/retriever.py) — if provided, widens the set of citations
            the CAPA Agent is allowed to draw on beyond just the 3
            hypotheses' source_ids.
        client: optional injected client exposing
            `.chat.completions.create(model=..., messages=...)` with the
            same interface as groq.Groq(). If omitted, a real Groq client
            is constructed from GROQ_API_KEY. Tests should always inject
            a mock client.

    Returns:
        list[dict]: validated CAPA items (see module docstring for shape).

    Raises:
        CapaAgentError: if valid output is not obtained within
            MAX_RETRIES attempts, or if GROQ_API_KEY is missing and no
            client was injected.
    """
    if jurisdiction not in ("US", "EU"):
        raise CapaAgentError(f"jurisdiction must be 'US' or 'EU', got '{jurisdiction}'")

    if client is None:
        client = _get_groq_client()

    valid_source_ids = _collect_valid_source_ids(investigation_output, context)

    user_payload = {
        "approved_root_cause": approved_root_cause,
        "investigation_output": investigation_output,
        "jurisdiction": jurisdiction,
    }
    if context:
        user_payload["rag_context"] = context

    messages = [
        {"role": "system", "content": CAPA_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload)},
    ]

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        raw_text = response.choices[0].message.content

        try:
            cleaned = _strip_code_fences(raw_text)
            parsed = json.loads(cleaned)
        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            last_error = f"Response was not valid JSON: {exc}. Raw response: {raw_text!r}"
            messages.append({"role": "assistant", "content": raw_text})
            messages.append({
                "role": "user",
                "content": (
                    f"Your previous response could not be parsed as JSON ({exc}). "
                    "Respond again with ONLY the JSON array, no markdown fences, no preamble."
                ),
            })
            continue

        validation_error = _validate_capa_output(parsed, valid_source_ids)
        if validation_error is None:
            return parsed

        last_error = validation_error
        messages.append({"role": "assistant", "content": raw_text})
        messages.append({
            "role": "user",
            "content": (
                f"Your previous response failed validation with these errors: "
                f"{last_error}. Respond again with ONLY a corrected JSON array. "
                "Remember: source_citations values must exactly match a source_id "
                "already cited in the investigation output, or a chunk_id/case_id "
                "from the provided RAG context — do not invent new identifiers."
            ),
        })

    raise CapaAgentError(
        f"CAPA Agent failed to produce valid output after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


if __name__ == "__main__":
    # Mock smoke tests — no real Groq API calls.
    class _FakeChoice:
        def __init__(self, content):
            self.message = type("Msg", (), {"content": content})()

    class _FakeResponse:
        def __init__(self, content):
            self.choices = [_FakeChoice(content)]

    class _FakeCompletions:
        def __init__(self, responses):
            self._responses = list(responses)
            self.call_count = 0

        def create(self, model, messages):
            self.call_count += 1
            content = self._responses[self.call_count - 1]
            return _FakeResponse(content)

    class _FakeChat:
        def __init__(self, responses):
            self.completions = _FakeCompletions(responses)

    class _FakeGroqClient:
        def __init__(self, responses):
            self.chat = _FakeChat(responses)

    investigation_output = {
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

    valid_capa_response = json.dumps([
        {
            "description": "Re-inspect and re-qualify packaging seal equipment on Line 3.",
            "type": "corrective",
            "responsible_role": "Production Supervisor",
            "due_date": "2024-07-10",
            "evidence_required": "Equipment requalification report",
            "effectiveness_metric": "Zero seal-related complaints in next 90 days",
            "source_citations": ["sop_qa_042_site_a_chunk_0000"],
        },
        {
            "description": "Implement automated seal-integrity check at end-of-line.",
            "type": "preventive",
            "responsible_role": "QA Manager",
            "due_date": "2024-08-15",
            "evidence_required": "Validation protocol and report for new check",
            "effectiveness_metric": "100% of batches pass automated seal check before release",
            "source_citations": ["fda_21cfr_211_chunk_0001", "CASE-2023-0451"],
        },
    ])

    # 1. Happy path
    happy_client = _FakeGroqClient([valid_capa_response])
    result = generate_capa("Packaging seal integrity failure", investigation_output, "US", client=happy_client)
    assert len(result) == 2
    assert happy_client.chat.completions.call_count == 1
    print("PASS: happy path returns valid CAPA plan on first attempt")

    # 2. Missing preventive type -> retry then valid
    corrective_only_response = json.dumps([json.loads(valid_capa_response)[0]])
    retry_client = _FakeGroqClient([corrective_only_response, valid_capa_response])
    result = generate_capa("Packaging seal integrity failure", investigation_output, "US", client=retry_client)
    assert retry_client.chat.completions.call_count == 2
    print("PASS: missing preventive-type action triggers retry, succeeds on attempt 2")

    # 3. Fabricated citation -> retry then valid
    fabricated_response = json.dumps([
        {**json.loads(valid_capa_response)[0], "source_citations": ["totally_fake_id_0000"]},
        json.loads(valid_capa_response)[1],
    ])
    retry_client_2 = _FakeGroqClient([fabricated_response, valid_capa_response])
    result = generate_capa("Packaging seal integrity failure", investigation_output, "US", client=retry_client_2)
    assert retry_client_2.chat.completions.call_count == 2
    print("PASS: fabricated source_citation triggers retry, succeeds on attempt 2")

    # 4. Missing required field -> retry then valid
    missing_field_item = dict(json.loads(valid_capa_response)[0])
    del missing_field_item["due_date"]
    missing_field_response = json.dumps([missing_field_item, json.loads(valid_capa_response)[1]])
    retry_client_3 = _FakeGroqClient([missing_field_response, valid_capa_response])
    result = generate_capa("Packaging seal integrity failure", investigation_output, "US", client=retry_client_3)
    assert retry_client_3.chat.completions.call_count == 2
    print("PASS: missing required field triggers retry, succeeds on attempt 2")

    # 5. Exhausts retries -> raises CapaAgentError
    always_bad_client = _FakeGroqClient([corrective_only_response, corrective_only_response, corrective_only_response])
    try:
        generate_capa("Packaging seal integrity failure", investigation_output, "US", client=always_bad_client)
        raise AssertionError("Expected CapaAgentError to be raised")
    except CapaAgentError:
        assert always_bad_client.chat.completions.call_count == MAX_RETRIES
        print(f"PASS: exhausts {MAX_RETRIES} retries and raises CapaAgentError")

    # 6. Invalid jurisdiction -> raises immediately, no API call
    no_call_client = _FakeGroqClient([])
    try:
        generate_capa("X", investigation_output, "UK", client=no_call_client)
        raise AssertionError("Expected CapaAgentError for invalid jurisdiction")
    except CapaAgentError:
        assert no_call_client.chat.completions.call_count == 0
        print("PASS: invalid jurisdiction rejected before any API call")

    print("\nAll capa_agent mock smoke tests passed.")