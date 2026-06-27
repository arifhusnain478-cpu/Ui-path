"""
RAG — Hybrid Search
Combines vector search (60%) + BM25 (40%) using Reciprocal Rank Fusion.
No duplicate chunks. Results sorted by combined score descending.
"""

from . import vector_store, bm25_search


def search(query: str, eligible_chunk_ids: list, top_k: int = 5) -> list:
    """
    Hybrid search: 0.6 * vector_score + 0.4 * bm25_rank_score.
    Returns top_k deduplicated chunks sorted by combined score.
    Each result: {chunk_id, source, doc_type, section, text, relevance_score, combined_score}
    """
    if not query.strip() or not eligible_chunk_ids:
        return []

    # Get results from both methods (fetch more than top_k to fuse properly)
    fetch_k = max(top_k * 3, 15)
    vector_results = vector_store.search(query, eligible_chunk_ids, top_k=fetch_k)
    bm25_results   = bm25_search.search(query, eligible_chunk_ids, top_k=fetch_k)

    # Build rank maps (rank 1 = best)
    vector_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(vector_results)}
    bm25_ranks   = {r["chunk_id"]: i + 1 for i, r in enumerate(bm25_results)}

    # Collect all unique chunk_ids
    all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())

    # Build lookup for chunk metadata (from whichever source has it)
    chunk_meta = {}
    for r in vector_results + bm25_results:
        chunk_meta[r["chunk_id"]] = r

    # Reciprocal Rank Fusion with 60/40 weighting
    K = 60  # RRF constant (standard value)
    scored = []
    for chunk_id in all_ids:
        v_rank = vector_ranks.get(chunk_id, fetch_k + 1)
        b_rank = bm25_ranks.get(chunk_id, fetch_k + 1)

        v_score = 0.6 * (1.0 / (K + v_rank))
        b_score = 0.4 * (1.0 / (K + b_rank))
        combined = round(v_score + b_score, 6)

        meta = chunk_meta[chunk_id]
        scored.append({
            "chunk_id":       chunk_id,
            "source":         meta.get("source", ""),
            "doc_type":       meta.get("doc_type", ""),
            "section":        meta.get("section", ""),
            "text":           meta.get("text", ""),
            "relevance_score": combined,   # use combined_score so context_builder confidence is non-zero
            "combined_score": combined,
        })

    scored.sort(key=lambda x: x["combined_score"], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).split("rag")[0])
    from backend.app.rag.jurisdiction_filter import filter as jfilter

    us_chunks = jfilter("US")
    results   = search("contamination investigation batch recall", us_chunks, top_k=5)

    print(f"Hybrid search — top {len(results)} results:")
    for r in results:
        print(f"  [{r['combined_score']:.5f}] {r['chunk_id']} ({r['doc_type']})")

    # No duplicates
    ids = [r["chunk_id"] for r in results]
    assert len(ids) == len(set(ids)), "Duplicate chunks found!"
    print("✅ hybrid_search test passed — no duplicates")
