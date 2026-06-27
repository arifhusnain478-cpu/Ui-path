"""
agents/intake_agent.py

Step 4c of the QualiTrace AI agent layer.

The Intake Agent is the first agent to touch a new complaint. It calls
Groq (model: llama-3.3-70b-versatile) with INTAKE_SYSTEM_PROMPT plus the
complaint record, and must return:
    risk_level:       one of "low" | "medium" | "high" | "critical"
    confidence_score: float 0.0-1.0

Retries up to 3 times on schema failure (malformed JSON, wrong risk_level
value, out-of-range confidence_score) before giving up.

API key is sourced from os.environ["GROQ_API_KEY"], loaded via a .env
file in the project root through python-dotenv. This module does NOT
read the key directly at import time — _get_groq_client() reads it lazily
so that:
  - importing this module (e.g. in tests) never requires a key to be set
  - a mock client can be injected via run_intake(..., client=...) without
    ever touching the real Groq SDK or network
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv

from .prompts import INTAKE_SYSTEM_PROMPT

# Load .env once at import time (does nothing if no .env file exists —
# dotenv silently no-ops, so this is safe in any environment).
load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


class IntakeAgentError(Exception):
    """Raised when the Intake Agent cannot produce a valid result after MAX_RETRIES attempts."""


def _get_groq_client():
    """
    Lazily constructs a real Groq client. Only called when run_intake() is
    invoked without an injected `client` — keeps this module importable
    and unit-testable with zero network/API-key dependency.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise IntakeAgentError(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(GROQ_API_KEY=your_key_here) or export it in your shell."
        )
    from groq import Groq  # imported lazily so this module doesn't hard-require
                             # the groq package just to be imported/tested
    return Groq(api_key=api_key)


def _validate_schema(parsed: dict) -> Optional[str]:
    """
    Validates the parsed Intake Agent output against the contract:
        { "risk_level": one of VALID_RISK_LEVELS, "confidence_score": float 0.0-1.0 }

    Returns None if valid, or a human-readable error string describing
    the first problem found (used to build the retry prompt).
    """
    if not isinstance(parsed, dict):
        return f"Expected a JSON object, got {type(parsed).__name__}"

    risk_level = parsed.get("risk_level")
    if risk_level not in VALID_RISK_LEVELS:
        return (
            f"'risk_level' must be one of {sorted(VALID_RISK_LEVELS)}, "
            f"got {risk_level!r}"
        )

    confidence_score = parsed.get("confidence_score")
    if isinstance(confidence_score, bool) or not isinstance(confidence_score, (int, float)):
        return f"'confidence_score' must be a float, got {type(confidence_score).__name__}"
    if not (0.0 <= float(confidence_score) <= 1.0):
        return f"'confidence_score' must be between 0.0 and 1.0, got {confidence_score}"

    return None


def _strip_code_fences(text: str) -> str:
    """Defensive cleanup in case the model wraps its JSON in ```json fences despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


def run_intake(complaint_record: dict, client=None) -> dict:
    """
    Runs the Intake Agent on a single complaint record.

    Args:
        complaint_record: dict describing the complaint. Expected to
            optionally include complaint_type, description, patient_impact,
            recurrence, product_type, jurisdiction, market_code,
            batch_number (per the few-shot examples in prompts.py).
        client: optional injected client object exposing
            `.chat.completions.create(model=..., messages=...)` returning
            an object with `.choices[0].message.content`. This matches the
            real groq.Groq() client's interface. If omitted, a real Groq
            client is constructed from GROQ_API_KEY. Tests should always
            inject a mock client here.

    Returns:
        dict: {"risk_level": str, "confidence_score": float}

    Raises:
        IntakeAgentError: if a schema-valid response is not obtained
            within MAX_RETRIES attempts, or if GROQ_API_KEY is missing
            and no client was injected.
    """
    if client is None:
        client = _get_groq_client()

    messages = [
        {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(complaint_record)},
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

        schema_error = _validate_schema(parsed)
        if schema_error is None:
            return {
                "risk_level": parsed["risk_level"],
                "confidence_score": float(parsed["confidence_score"]),
            }

        last_error = schema_error
        messages.append({"role": "assistant", "content": raw_text})
        messages.append({
            "role": "user",
            "content": (
                f"Your previous response failed validation: {schema_error}. "
                "Respond again with ONLY a corrected JSON object matching the contract exactly."
            ),
        })

    raise IntakeAgentError(
        f"Intake Agent failed to produce valid output after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


if __name__ == "__main__":
    # Mock smoke tests — no real Groq API calls. Verifies retry logic,
    # schema validation, and the happy path using an injected fake client.
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
        "complaint_type": "contamination",
        "patient_impact": True,
        "recurrence": False,
        "product_type": "sterile_injectable",
        "description": "Foreign particle observed in sterile injectable vial.",
        "jurisdiction": "US",
    }

    # 1. Happy path: valid JSON on first try
    happy_client = _FakeGroqClient([
        '{"risk_level": "critical", "confidence_score": 0.95}',
    ])
    result = run_intake(complaint, client=happy_client)
    assert result == {"risk_level": "critical", "confidence_score": 0.95}, result
    assert happy_client.chat.completions.call_count == 1
    print(f"PASS: happy path -> {result}")

    # 2. Retry path: malformed JSON then markdown-fenced JSON then valid
    retry_client = _FakeGroqClient([
        "not json at all",
        '```json\n{"risk_level": "high", "confidence_score": 0.8}\n```',
    ])
    result = run_intake(complaint, client=retry_client)
    assert result == {"risk_level": "high", "confidence_score": 0.8}, result
    assert retry_client.chat.completions.call_count == 2
    print(f"PASS: retry on malformed JSON, succeeds on attempt 2 -> {result}")

    # 3. Retry path: invalid risk_level value then valid
    bad_value_client = _FakeGroqClient([
        '{"risk_level": "severe", "confidence_score": 0.7}',
        '{"risk_level": "medium", "confidence_score": 0.7}',
    ])
    result = run_intake(complaint, client=bad_value_client)
    assert result == {"risk_level": "medium", "confidence_score": 0.7}, result
    assert bad_value_client.chat.completions.call_count == 2
    print(f"PASS: retry on invalid risk_level value, succeeds on attempt 2 -> {result}")

    # 4. Out-of-range confidence_score then valid
    bad_conf_client = _FakeGroqClient([
        '{"risk_level": "low", "confidence_score": 1.5}',
        '{"risk_level": "low", "confidence_score": 0.6}',
    ])
    result = run_intake(complaint, client=bad_conf_client)
    assert result == {"risk_level": "low", "confidence_score": 0.6}, result
    print(f"PASS: retry on out-of-range confidence_score, succeeds on attempt 2 -> {result}")

    # 5. Exhausts all 3 retries -> raises IntakeAgentError
    always_bad_client = _FakeGroqClient([
        '{"risk_level": "invalid", "confidence_score": 0.5}',
        '{"risk_level": "invalid", "confidence_score": 0.5}',
        '{"risk_level": "invalid", "confidence_score": 0.5}',
    ])
    try:
        run_intake(complaint, client=always_bad_client)
        raise AssertionError("Expected IntakeAgentError to be raised")
    except IntakeAgentError as exc:
        assert always_bad_client.chat.completions.call_count == MAX_RETRIES
        print(f"PASS: exhausts {MAX_RETRIES} retries and raises IntakeAgentError -> {exc}")

    print("\nAll intake_agent mock smoke tests passed.")
