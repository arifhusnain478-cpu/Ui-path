import os
"""
RAG — BM25 Keyword Search
Keyword-based search over chunks, filtered to eligible chunk_ids.
Empty query returns empty list safely.
"""

import json
import pickle
import numpy as np
from pathlib import Path

PROCESSED_DIR = Path(os.environ.get("QUALITRACE_KNOWLEDGE_DIR", str(Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge" / "processed")))

_bm25        = None
_chunks      = None
_chunk_index = None
_id_to_pos   = None


def _load():
    global _bm25, _chunks, _chunk_index, _id_to_pos
    if _bm25 is not None:
        return

    with open(PROCESSED_DIR / "bm25_index.pkl", "rb") as f:
        _bm25 = pickle.load(f)

    with open(PROCESSED_DIR / "chunks.json") as f:
        _chunks = {c["chunk_id"]: c for c in json.load(f)}

    with open(PROCESSED_DIR / "chunk_index.json") as f:
        raw = json.load(f)
        _chunk_index = {int(k): v for k, v in raw.items()}
        _id_to_pos   = {v: int(k) for k, v in raw.items()}


def search(query: str, eligible_chunk_ids: list, top_k: int = 5) -> list:
    """
    Returns ranked chunks matching query using BM25.
    Only searches within eligible_chunk_ids.
    Empty query returns []. Never crashes.
    Each result: {chunk_id, source, doc_type, section, text, bm25_score}
    """
    _load()

    if not query.strip() or not eligible_chunk_ids:
        return []

    tokenized_query = query.lower().split()

    # Get all BM25 scores (over all 75 chunks)
    all_scores = _bm25.get_scores(tokenized_query)

    # Filter to eligible positions only
    eligible_positions = [
        _id_to_pos[cid] for cid in eligible_chunk_ids
        if cid in _id_to_pos
    ]
    if not eligible_positions:
        return []

    # Extract scores for eligible chunks and rank
    eligible_scores = [(pos, all_scores[pos]) for pos in eligible_positions]
    eligible_scores.sort(key=lambda x: x[1], reverse=True)
    top = eligible_scores[:top_k]

    results = []
    for pos, score in top:
        chunk_id = _chunk_index[pos]
        chunk    = _chunks.get(chunk_id, {})
        results.append({
            "chunk_id":   chunk_id,
            "source":     chunk.get("doc_id", chunk_id),
            "doc_type":   chunk.get("doc_type", "UNKNOWN"),
            "section":    chunk.get("section_number", ""),
            "text":       chunk.get("text", ""),
            "bm25_score": float(round(float(score), 4)),
        })

    return results


if __name__ == "__main__":
    from jurisdiction_filter import filter as jfilter
    us_chunks = jfilter("US")

    # Test 1: specific regulatory query
    results = search("21 CFR 211.198 complaint files", us_chunks, top_k=3)
    print(f"BM25 results for '21 CFR 211.198':")
    for r in results:
        print(f"  [{r['bm25_score']:.3f}] {r['chunk_id']}")

    # Test 2: empty query must not crash
    empty = search("", us_chunks)
    assert empty == [], "Empty query should return []"

    print("✅ bm25_search test passed")
