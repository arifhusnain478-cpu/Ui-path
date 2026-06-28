"""
knowledge/scripts/build_bm25.py
Builds BM25 index from chunks.json. Saves bm25_index.pkl
"""
import json
import pickle
import sys
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "processed"


def main():
    chunks_path = PROCESSED_DIR / "chunks.json"
    if not chunks_path.exists():
        print(f"ERROR: {chunks_path} not found. Run chunk_docs.py first.")
        sys.exit(1)

    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        print("ERROR: rank-bm25 not installed. Run: pip install rank-bm25")
        sys.exit(1)

    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Building BM25 index for {len(chunks)} chunks...")

    tokenized_corpus = []
    for chunk in chunks:
        text = chunk["text"] + " " + " ".join(chunk.get("keywords", []))
        tokens = text.lower().split()
        tokenized_corpus.append(tokens)

    bm25 = BM25Okapi(tokenized_corpus)

    index_data = {
        "bm25": bm25,
        "chunk_ids": [c["chunk_id"] for c in chunks],
    }

    bm25_path = PROCESSED_DIR / "bm25_index.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(index_data, f)

    print(f"✅ BM25 index built → {bm25_path}")


if __name__ == "__main__":
    main()
