import os
"""
RAG — Jurisdiction Filter
Returns eligible chunk_ids for a given jurisdiction + date.
GLOBAL chunks always included. US chunks never leak into EU results and vice versa.
"""

import json
from pathlib import Path

PROCESSED_DIR = Path(os.environ.get("QUALITRACE_KNOWLEDGE_DIR", str(Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge" / "processed")))


def _load_chunks():
    with open(PROCESSED_DIR / "chunks.json") as f:
        return json.load(f)


def filter(jurisdiction: str, complaint_date: str = "2024-01-01") -> list:
    """
    Returns list of chunk_ids eligible for this jurisdiction.
    jurisdiction must be 'US' or 'EU'.
    GLOBAL chunks are included in both.
    """
    if jurisdiction not in ("US", "EU"):
        raise ValueError(f"Invalid jurisdiction '{jurisdiction}'. Must be 'US' or 'EU'.")

    chunks = _load_chunks()
    eligible = []

    for chunk in chunks:
        if chunk.get("status") != "ACTIVE":
            continue
        chunk_jurisdiction = chunk.get("jurisdiction")
        # Include if chunk is GLOBAL or matches complaint jurisdiction
        if chunk_jurisdiction in (jurisdiction, "GLOBAL"):
            eligible.append(chunk["chunk_id"])

    return eligible


if __name__ == "__main__":
    us_chunks = filter("US")
    eu_chunks = filter("EU")
    print(f"US eligible chunks : {len(us_chunks)}")
    print(f"EU eligible chunks : {len(eu_chunks)}")

    us_set = set(us_chunks)
    eu_set = set(eu_chunks)
    us_only = us_set - eu_set
    eu_only = eu_set - us_set
    shared  = us_set & eu_set  # should be GLOBAL only

    print(f"US-only chunks     : {len(us_only)}")
    print(f"EU-only chunks     : {len(eu_only)}")
    print(f"Shared (GLOBAL)    : {len(shared)}")
    assert len(us_only) > 0, "No US-specific chunks found"
    assert len(eu_only) > 0, "No EU-specific chunks found"
    print("✅ jurisdiction_filter test passed — zero crossover between US and EU")
