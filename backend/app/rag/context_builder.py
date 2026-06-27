import os
"""
RAG — Context Builder
Formats retrieved chunks + historical cases into the exact contract
that the Investigation Agent expects. Field names must never change.
"""

from typing import Optional


def build(
    complaint_record: dict,
    retrieved_chunks: list,
    historical_cases: list,
) -> dict:
    """
    Builds the RAG context object passed to investigation_agent.py.

    Output contract (MUST match investigation_agent.py input exactly):
    {
      "query":             str,
      "jurisdiction":      "US" | "EU",
      "retrieved_chunks":  list of chunk dicts,
      "historical_cases":  list of case dicts,
      "confidence_score":  float 0.0-1.0,
      "source_list":       list of "filename — section" strings
    }
    """
    jurisdiction = complaint_record.get("jurisdiction") or \
                   _infer_jurisdiction(complaint_record.get("market_code", "US"))

    query = _build_query(complaint_record)

    # Normalize retrieved_chunks to contract shape
    normalized_chunks = []
    for chunk in retrieved_chunks:
        normalized_chunks.append({
            "chunk_id":       chunk.get("chunk_id", ""),
            "source":         chunk.get("source", chunk.get("doc_id", "")),
            "doc_type":       chunk.get("doc_type", "UNKNOWN"),
            "section":        chunk.get("section", chunk.get("section_number", "")),
            "text":           chunk.get("text", ""),
            "relevance_score": float(chunk.get("relevance_score", chunk.get("combined_score", 0.0))),
        })

    # Normalize historical_cases to contract shape
    normalized_cases = []
    for case in historical_cases:
        normalized_cases.append({
            "case_id":         case.get("case_id", ""),
            "similarity_score": float(case.get("similarity_score", 0.0)),
            "outcome":         case.get("outcome", ""),
            "root_cause":      case.get("root_cause", case.get("root_cause_summary", "")),
        })

    # Build source_list — "filename — section" strings, deduplicated
    source_list = []
    seen = set()
    for chunk in normalized_chunks:
        entry = f"{chunk['source']} — Section {chunk['section']}"
        if entry not in seen:
            source_list.append(entry)
            seen.add(entry)

    # Confidence score: average of top chunk relevance scores
    confidence_score = _compute_confidence(normalized_chunks)

    return {
        "query":            query,
        "jurisdiction":     jurisdiction,
        "retrieved_chunks": normalized_chunks,
        "historical_cases": normalized_cases,
        "confidence_score": confidence_score,
        "source_list":      source_list,
    }


def _build_query(complaint_record: dict) -> str:
    """Build a search query string from complaint fields."""
    parts = []
    if complaint_record.get("complaint_type"):
        parts.append(complaint_record["complaint_type"])
    if complaint_record.get("description"):
        parts.append(complaint_record["description"][:200])
    if complaint_record.get("product_name"):
        parts.append(complaint_record["product_name"])
    return " ".join(parts) if parts else "pharmaceutical complaint investigation"


def _infer_jurisdiction(market_code: str) -> str:
    """Map market_code to jurisdiction."""
    us_codes = {"US", "CA"}
    eu_codes = {"EU", "DE", "FR", "IT", "ES", "UK"}
    code = (market_code or "US").upper()
    if code in eu_codes:
        return "EU"
    return "US"


def _compute_confidence(chunks: list) -> float:
    """
    Confidence based on top chunk relevance scores.
    Returns 0.0 if no chunks. Flags low confidence below 0.6.
    """
    if not chunks:
        return 0.0
    scores = [c["relevance_score"] for c in chunks[:5]]
    avg = sum(scores) / len(scores)
    return round(float(avg), 4)


if __name__ == "__main__":
    # Quick contract validation test
    complaint = {
        "complaint_id":   "TEST-001",
        "product_name":   "Metformin 500mg",
        "complaint_type": "contamination",
        "description":    "Foreign particle found in tablet bottle",
        "market_code":    "US",
        "jurisdiction":   "US",
        "patient_impact": False,
    }
    mock_chunks = [
        {"chunk_id": "fda_21cfr_211_chunk_0001", "source": "fda_21cfr_211",
         "doc_type": "REGULATION", "section": "3", "text": "Complaint investigation...",
         "relevance_score": 0.82},
        {"chunk_id": "sop_qa_042_site_a_chunk_0000", "source": "sop_qa_042_site_a",
         "doc_type": "SOP", "section": "1", "text": "Intake procedure...",
         "relevance_score": 0.75},
    ]
    mock_cases = [
        {"case_id": "CASE-2023-0451", "similarity_score": 0.88,
         "outcome": "effective", "root_cause": "Packaging seal failure"},
    ]

    ctx = build(complaint, mock_chunks, mock_cases)

    # Validate all 6 required fields present
    required = {"query", "jurisdiction", "retrieved_chunks", "historical_cases",
                "confidence_score", "source_list"}
    assert required == set(ctx.keys()), f"Missing fields: {required - set(ctx.keys())}"
    assert ctx["jurisdiction"] in ("US", "EU")
    assert 0.0 <= ctx["confidence_score"] <= 1.0
    assert len(ctx["retrieved_chunks"]) == 2
    assert len(ctx["source_list"]) == 2

    print("Context output:")
    import json
    print(json.dumps({k: v for k, v in ctx.items() if k != "retrieved_chunks"}, indent=2))
    print("✅ context_builder contract test passed")
