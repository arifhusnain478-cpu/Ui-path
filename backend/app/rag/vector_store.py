import os
"""
RAG — Vector Store
Cosine similarity search using TF-IDF + SVD embeddings.
Filters to eligible chunk_ids before searching.
"""

import json
import pickle
import numpy as np
from pathlib import Path
from sklearn.preprocessing import normalize

PROCESSED_DIR = Path(os.environ.get("QUALITRACE_KNOWLEDGE_DIR", str(Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge" / "processed")))

# Module-level cache so files load once
_chunks      = None
_embeddings  = None
_chunk_index = None  # int position → chunk_id
_id_to_pos   = None  # chunk_id → int position
_vectorizer  = None
_svd         = None


def _load():
    global _chunks, _embeddings, _chunk_index, _id_to_pos, _vectorizer, _svd
    if _chunks is not None:
        return

    with open(PROCESSED_DIR / "chunks.json") as f:
        _chunks = {c["chunk_id"]: c for c in json.load(f)}

    _embeddings = np.load(str(PROCESSED_DIR / "embeddings.npy"))

    with open(PROCESSED_DIR / "chunk_index.json") as f:
        raw = json.load(f)
        _chunk_index = {int(k): v for k, v in raw.items()}
        _id_to_pos   = {v: int(k) for k, v in raw.items()}

    with open(PROCESSED_DIR / "tfidf_vectorizer.pkl", "rb") as f:
        _vectorizer = pickle.load(f)

    with open(PROCESSED_DIR / "svd_model.pkl", "rb") as f:
        _svd = pickle.load(f)


def _encode_query(query: str) -> np.ndarray:
    """Encode a query string using the same TF-IDF + SVD pipeline as ingest."""
    tfidf_vec = _vectorizer.transform([query])
    svd_vec   = _svd.transform(tfidf_vec)
    normed    = normalize(svd_vec)
    # Pad to 384 if needed
    if normed.shape[1] < 384:
        pad = np.zeros((1, 384 - normed.shape[1]))
        normed = np.hstack([normed, pad])
    return normed[0].astype(np.float32)


def search(query: str, eligible_chunk_ids: list, top_k: int = 5) -> list:
    """
    Returns top_k chunks by cosine similarity to query.
    Only searches within eligible_chunk_ids.
    Each result: {chunk_id, source, doc_type, section, text, relevance_score}
    """
    _load()

    if not query.strip() or not eligible_chunk_ids:
        return []

    # Get positions for eligible chunks
    eligible_positions = [
        _id_to_pos[cid] for cid in eligible_chunk_ids
        if cid in _id_to_pos
    ]
    if not eligible_positions:
        return []

    query_vec  = _encode_query(query)
    subset_emb = _embeddings[eligible_positions]  # shape (n_eligible, 384)

    # Cosine similarity (embeddings already L2-normalized)
    scores = subset_emb @ query_vec  # dot product = cosine sim when normalized

    top_k_actual = min(top_k, len(scores))
    top_indices  = np.argsort(scores)[::-1][:top_k_actual]

    results = []
    for idx in top_indices:
        chunk_id = eligible_chunk_ids[idx]
        chunk    = _chunks.get(chunk_id, {})
        results.append({
            "chunk_id":       chunk_id,
            "source":         chunk.get("doc_id", chunk_id),
            "doc_type":       chunk.get("doc_type", "UNKNOWN"),
            "section":        chunk.get("section_number", ""),
            "text":           chunk.get("text", ""),
            "relevance_score": float(round(float(scores[idx]), 4)),
        })

    return results


if __name__ == "__main__":
    from jurisdiction_filter import filter as jfilter
    us_chunks = jfilter("US")
    results   = search("contamination complaint investigation", us_chunks, top_k=3)
    print(f"Top {len(results)} results for US contamination query:")
    for r in results:
        print(f"  [{r['relevance_score']:.3f}] {r['chunk_id']} — {r['doc_type']}")
    assert all(0.0 <= r["relevance_score"] <= 1.0 for r in results)
    print("✅ vector_store test passed")
