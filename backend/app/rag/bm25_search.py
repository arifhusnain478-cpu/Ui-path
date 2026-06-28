"""
RAG — BM25 Keyword Search
Keyword-based search over chunks, filtered to eligible chunk_ids.
Empty query returns empty list safely.
"""

import os
import json
import pickle
import numpy as np
from pathlib import Path

PROCESSED_DIR = Path("D:/Hackthon of summer vacation/Ui-path/knowledge/processed")

_bm25           = None
_chunks         = None
_chunk_index    = None
_id_to_pos      = None
_bm25_chunk_ids = None


def _load():
    global _bm25, _chunks, _chunk_index, _id_to_pos, _bm25_chunk_ids
    if _bm25 is not None:
        return

    with open(PROCESSED_DIR / "bm25_index.pkl", "rb") as f:
        _tmp = pickle.load(f)
        _bm25 = _tmp["bm25"]
        _bm25_chunk_ids = _tmp["chunk_ids"]

    with open(PROCESSED_DIR / "chunks.json", encoding="utf-8") as f:
        _chunks = {c["chunk_id"]: c for c in json.load(f)}

    with open(PROCESSED_DIR / "chunk_index.json") as f:
        raw = json.load(f)
        _chunk_index = {k: v for k, v in raw.items()}
        _id_to_pos   = {v: k for k, v in raw.items()}


def search(query: str, eligible_chunk_ids: list, top_k: int = 5) -> list:
    _load()

    if not query.strip() or not eligible_chunk_ids:
        return []

    tokenized_query = query.lower().split()
    all_scores = _bm25.get_scores(tokenized_query)

    eligible_set = set(eligible_chunk_ids)
    eligible_scores = [
        (i, all_scores[i], _bm25_chunk_ids[i])
        for i in range(len(_bm25_chunk_ids))
        if _bm25_chunk_ids[i] in eligible_set
    ]

    eligible_scores.sort(key=lambda x: x[1], reverse=True)
    top = eligible_scores[:top_k]

    results = []
    for _, score, chunk_id in top:
        chunk = _chunks.get(chunk_id, {})
        results.append({
            "chunk_id":   chunk_id,
            "source":     chunk.get("doc_id", chunk_id),
            "doc_type":   chunk.get("doc_type", "UNKNOWN"),
            "section":    chunk.get("section_number", ""),
            "text":       chunk.get("text", ""),
            "bm25_score": float(round(float(score), 4)),
        })

    return results