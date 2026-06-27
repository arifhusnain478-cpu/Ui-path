import os
"""
RAG — Retriever
Single entry point for the entire RAG pipeline.
Call: retrieve(complaint_record) → context dict

Pipeline: jurisdiction_filter → hybrid_search → historical_cases → context_builder
Performance target: under 3 seconds.
Graceful error if knowledge store is empty.
"""

import time
import json
from pathlib import Path

from . import jurisdiction_filter, hybrid_search, context_builder

DATASETS_DIR = Path(__file__).parent.parent.parent.parent.parent / "datasets"


def retrieve(complaint_record: dict) -> dict:
    """
    Full RAG pipeline. Returns context dict matching Investigation Agent contract.
    Never crashes — returns error dict on failure.
    """
    start = time.time()

    try:
        # ── 1. Determine jurisdiction ──────────────────────────────────────────
        jurisdiction = complaint_record.get("jurisdiction") or \
                       _infer_jurisdiction(complaint_record.get("market_code", "US"))

        # ── 2. Filter eligible chunks by jurisdiction ──────────────────────────
        eligible_ids = jurisdiction_filter.filter(jurisdiction)

        if not eligible_ids:
            return _empty_context(complaint_record, jurisdiction,
                                  reason="No eligible chunks for jurisdiction")

        # ── 3. Hybrid search ───────────────────────────────────────────────────
        query = _build_query(complaint_record)
        retrieved_chunks = hybrid_search.search(query, eligible_ids, top_k=5)

        if not retrieved_chunks:
            return _empty_context(complaint_record, jurisdiction,
                                  reason="No chunks retrieved from hybrid search")

        # ── 4. Historical case search ──────────────────────────────────────────
        historical_cases = _search_historical_cases(complaint_record)

        # ── 5. Build context ───────────────────────────────────────────────────
        ctx = context_builder.build(complaint_record, retrieved_chunks, historical_cases)

        elapsed = round(time.time() - start, 3)
        ctx["_retrieval_time_seconds"] = elapsed

        if elapsed > 3.0:
            print(f"⚠️  Warning: retrieval took {elapsed}s (target: <3s)")

        return ctx

    except Exception as e:
        return {
            "query":            complaint_record.get("description", ""),
            "jurisdiction":     complaint_record.get("jurisdiction", "US"),
            "retrieved_chunks": [],
            "historical_cases": [],
            "confidence_score": 0.0,
            "source_list":      [],
            "error":            str(e),
            "_retrieval_time_seconds": round(time.time() - start, 3),
        }


def _build_query(complaint_record: dict) -> str:
    parts = []
    if complaint_record.get("complaint_type"):
        parts.append(complaint_record["complaint_type"])
    if complaint_record.get("description"):
        parts.append(complaint_record["description"][:300])
    if complaint_record.get("product_name"):
        parts.append(complaint_record["product_name"])
    return " ".join(parts) if parts else "pharmaceutical complaint"


def _infer_jurisdiction(market_code: str) -> str:
    eu_codes = {"EU", "DE", "FR", "IT", "ES", "UK"}
    return "EU" if (market_code or "").upper() in eu_codes else "US"


def _search_historical_cases(complaint_record: dict) -> list:
    """
    Simple keyword-based historical case matching.
    Looks for cases with same complaint_type and jurisdiction.
    Returns up to 3 most relevant historical cases.
    """
    seed_path = DATASETS_DIR / "historical_cases_seed.json"
    if not seed_path.exists():
        return []

    try:
        with open(seed_path) as f:
            all_cases = json.load(f)

        complaint_type = complaint_record.get("complaint_type", "")
        jurisdiction   = complaint_record.get("jurisdiction", "US")

        matched = []
        for case in all_cases:
            score = 0.0
            if case.get("jurisdiction") == jurisdiction:
                score += 0.5
            if case.get("complaint_type") == complaint_type:
                score += 0.4
            if case.get("outcome") == "effective":
                score += 0.1
            if score > 0:
                matched.append({
                    "case_id":         case.get("case_id", ""),
                    "similarity_score": round(score, 2),
                    "outcome":         case.get("outcome", ""),
                    "root_cause":      case.get("root_cause", ""),
                })

        matched.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matched[:3]

    except Exception:
        return []


def _empty_context(complaint_record: dict, jurisdiction: str, reason: str) -> dict:
    return {
        "query":            complaint_record.get("description", ""),
        "jurisdiction":     jurisdiction,
        "retrieved_chunks": [],
        "historical_cases": [],
        "confidence_score": 0.0,
        "source_list":      [],
        "insufficient_evidence": True,
        "reason":           reason,
    }


if __name__ == "__main__":
    import json

    # Test US complaint
    us_complaint = {
        "complaint_id":   "TEST-001",
        "product_name":   "Metformin 500mg",
        "batch_number":   "MF-2024-0892",
        "market_code":    "US",
        "jurisdiction":   "US",
        "complaint_type": "contamination",
        "patient_impact": False,
        "description":    "Foreign particle found in tablet bottle",
    }

    # Test EU complaint
    eu_complaint = {
        "complaint_id":   "TEST-002",
        "product_name":   "Amlodipine 10mg",
        "batch_number":   "AM-2024-0101",
        "market_code":    "EU",
        "jurisdiction":   "EU",
        "complaint_type": "quality",
        "patient_impact": False,
        "description":    "Tablet fragmentation on blister pack",
    }

    print("=" * 50)
    print("Testing US complaint retrieval...")
    us_ctx = retrieve(us_complaint)
    print(f"  Jurisdiction    : {us_ctx['jurisdiction']}")
    print(f"  Chunks retrieved: {len(us_ctx['retrieved_chunks'])}")
    print(f"  Confidence      : {us_ctx['confidence_score']}")
    print(f"  Time            : {us_ctx.get('_retrieval_time_seconds')}s")
    print(f"  Sources         : {us_ctx['source_list'][:2]}")

    # Verify no EU chunks in US result
    for chunk in us_ctx["retrieved_chunks"]:
        assert "eu" not in chunk["chunk_id"].lower() or "global" in chunk["chunk_id"].lower(), \
            f"EU chunk found in US results: {chunk['chunk_id']}"

    print("\nTesting EU complaint retrieval...")
    eu_ctx = retrieve(eu_complaint)
    print(f"  Jurisdiction    : {eu_ctx['jurisdiction']}")
    print(f"  Chunks retrieved: {len(eu_ctx['retrieved_chunks'])}")
    print(f"  Confidence      : {eu_ctx['confidence_score']}")
    print(f"  Time            : {eu_ctx.get('_retrieval_time_seconds')}s")

    assert us_ctx.get("_retrieval_time_seconds", 99) < 3.0, "US retrieval too slow"
    assert eu_ctx.get("_retrieval_time_seconds", 99) < 3.0, "EU retrieval too slow"
    assert us_ctx["jurisdiction"] == "US"
    assert eu_ctx["jurisdiction"] == "EU"

    print("\n✅ retriever.py end-to-end test passed")
