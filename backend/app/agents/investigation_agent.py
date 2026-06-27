"""
agents/investigation_agent.py

Step 4d of the QualiTrace AI agent layer.

The Investigation Agent receives a complaint record plus the full RAG
context object produced by rag/retriever.py (which in turn is built by
rag/context_builder.py), calls Groq (model: llama-3.3-70b-versatile) with
INVESTIGATION_SYSTEM_PROMPT, and validates the result with
agents/output_validator.py. Retries up to 3 times on validation failure,
feeding the validator's specific errors back to the model each time.

Output (on success):
    {
      "evidence_summary": str,
      "root_cause_hypotheses": [exactly 3 of {"hypothesis", "source_id", "likelihood"}],
      "overall_confidence": float 0.0-1.0,
      "conflicting_sources": [...],
      "escalation_required": bool,
      "escalation_reason": str
    }

API key sourced from os.environ["GROQ_API_KEY"] via .env, read lazily —
mirrors intake_agent.py's approach so importing this module never
requires a key, and a mock client can be injected for testing.
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv

from .prompts import INVESTIGATION_SYSTEM_PROMPT
from .output_validator import validate as validate_investigation_output

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_RETRIES = 3


class InvestigationAgentError(Exception):
    """Raised when the Investigation Agent cannot produce valid output after MAX_RETRIES attempts."""


def _get_groq_client():
    """
    Lazily constructs a real Groq client. Only called when investigate()
    is invoked without an injected `client`.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise InvestigationAgentError(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(GROQ_API_KEY=your_key_here) or export it in your shell."
        )
    from groq import Groq
    return Groq(api_key=api_key)


def _strip_code_fences(text: str) -> str:
    """Defensive cleanup in case the model wraps its JSON in ```json fences despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


def investigate(complaint_record: dict, context: dict, client=None) -> dict:
    """
    Runs the Investigation Agent on a single complaint, given the RAG
    context retrieved for it.

    Args:
        complaint_record: dict describing the complaint (case_id,
            complaint_type, description, jurisdiction, etc).
        context: the RAG context dict produced by rag/retriever.py /
            rag/context_builder.py:
            { query, jurisdiction, retrieved_chunks, historical_cases,
              confidence_score, source_list }
        client: optional injected client exposing
            `.chat.completions.create(model=..., messages=...)` with the
            same interface as groq.Groq(). If omitted, a real Groq client
            is constructed from GROQ_API_KEY. Tests should always inject
            a mock client.

    Returns:
        dict: validated Investigation Agent output (see module docstring
            for the exact shape).

    Raises:
        InvestigationAgentError: if valid output is not obtained within
            MAX_RETRIES attempts, or if GROQ_API_KEY is missing and no
            client was injected.
    """
    if client is None:
        client = _get_groq_client()

    user_payload = {
        "complaint_record": complaint_record,
        "rag_context": context,
    }

    messages = [
        {"role": "system", "content": INVESTIGATION_SYSTEM_PROMPT},
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
                    "Respond again with ONLY the JSON object, no markdown fences, no preamble."
                ),
            })
            continue

        result = validate_investigation_output(parsed, context)
        if result.is_valid:
            return parsed

        last_error = "; ".join(result.errors)
        messages.append({"role": "assistant", "content": raw_text})
        messages.append({
            "role": "user",
            "content": (
                "Your previous response failed validation with these errors: "
                f"{last_error}. Respond again with ONLY a corrected JSON object. "
                "Remember: source_id values must exactly match a chunk_id from "
                "retrieved_chunks or a case_id from historical_cases in the "
                "provided context — do not invent new identifiers."
            ),
        })

    raise InvestigationAgentError(
        f"Investigation Agent failed to produce valid output after {MAX_RETRIES} attempts. "
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

    complaint = {
        "case_id": "C-001",
        "complaint_type": "contamination",
        "description": "Foreign particle found in tablet bottle",
        "jurisdiction": "US",
    }

    mock_context = {
        "query": "contamination tablet bottle",
        "jurisdiction": "US",
        "retrieved_chunks": [
            {"chunk_id": "fda_21cfr_211_chunk_0001", "source": "fda_21cfr_211",
             "doc_type": "REGULATION", "section": "3", "text": "Complaint investigation...",
             "relevance_score": 0.82},
            {"chunk_id": "sop_qa_042_site_a_chunk_0000", "source": "sop_qa_042_site_a",
             "doc_type": "SOP", "section": "1", "text": "Intake procedure...",
             "relevance_score": 0.75},
        ],
        "historical_cases": [
            {"case_id": "CASE-2023-0451", "similarity_score": 0.88,
             "outcome": "effective", "root_cause": "Packaging seal failure"},
        ],
        "confidence_score": 0.785,
        "source_list": ["fda_21cfr_211 — Section 3", "sop_qa_042_site_a — Section 1"],
    }

    valid_response = json.dumps({
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
    })

    # 1. Happy path
    happy_client = _FakeGroqClient([valid_response])
    result = investigate(complaint, mock_context, client=happy_client)
    assert len(result["root_cause_hypotheses"]) == 3
    assert happy_client.chat.completions.call_count == 1
    print("PASS: happy path returns valid output on first attempt")

    # 2. Retry path: fabricated source_id then valid
    fabricated_response = json.dumps({
        "evidence_summary": "Made up.",
        "root_cause_hypotheses": [
            {"hypothesis": "Made up cause", "source_id": "totally_fake_chunk_9999", "likelihood": "high"},
            {"hypothesis": "Similar root cause as prior packaging case",
             "source_id": "CASE-2023-0451", "likelihood": "medium"},
            {"hypothesis": "Possible deviation from CGMP complaint handling",
             "source_id": "fda_21cfr_211_chunk_0001", "likelihood": "low"},
        ],
        "overall_confidence": 0.78,
        "conflicting_sources": [],
        "escalation_required": False,
        "escalation_reason": "",
    })
    retry_client = _FakeGroqClient([fabricated_response, valid_response])
    result = investigate(complaint, mock_context, client=retry_client)
    assert retry_client.chat.completions.call_count == 2
    print("PASS: fabricated source_id triggers retry, succeeds on attempt 2")

    # 3. Retry path: wrong hypothesis count then valid
    wrong_count_response = json.dumps({
        "evidence_summary": "Evidence points to a packaging seal failure.",
        "root_cause_hypotheses": json.loads(valid_response)["root_cause_hypotheses"][:2],
        "overall_confidence": 0.78,
        "conflicting_sources": [],
        "escalation_required": False,
        "escalation_reason": "",
    })
    retry_client_2 = _FakeGroqClient([wrong_count_response, valid_response])
    result = investigate(complaint, mock_context, client=retry_client_2)
    assert retry_client_2.chat.completions.call_count == 2
    print("PASS: wrong hypothesis count triggers retry, succeeds on attempt 2")

    # 4. Malformed JSON then valid
    malformed_client = _FakeGroqClient(["not json", valid_response])
    result = investigate(complaint, mock_context, client=malformed_client)
    assert malformed_client.chat.completions.call_count == 2
    print("PASS: malformed JSON triggers retry, succeeds on attempt 2")

    # 5. Exhausts all retries -> raises InvestigationAgentError
    always_bad_client = _FakeGroqClient([fabricated_response, fabricated_response, fabricated_response])
    try:
        investigate(complaint, mock_context, client=always_bad_client)
        raise AssertionError("Expected InvestigationAgentError to be raised")
    except InvestigationAgentError as exc:
        assert always_bad_client.chat.completions.call_count == MAX_RETRIES
        print(f"PASS: exhausts {MAX_RETRIES} retries and raises InvestigationAgentError")

    print("\nAll investigation_agent mock smoke tests passed.")
