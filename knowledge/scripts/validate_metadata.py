"""
knowledge/scripts/validate_metadata.py
Validates all processed knowledge base files.
"""
import json
import sys
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "processed"


def main():
    errors = []

    # Check required files
    required_files = ["chunks.json", "embeddings.npy", "chunk_index.json", "bm25_index.pkl", "doc_metadata.json"]
    for fname in required_files:
        fpath = PROCESSED_DIR / fname
        if not fpath.exists():
            errors.append(f"Missing file: {fname}")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    # Validate chunks
    with open(PROCESSED_DIR / "chunks.json", encoding="utf-8") as f:
        chunks = json.load(f)

    required_chunk_fields = ["chunk_id", "doc_id", "jurisdiction", "text", "status"]
    for i, chunk in enumerate(chunks):
        for field in required_chunk_fields:
            if field not in chunk:
                errors.append(f"Chunk {i} missing field: {field}")
        if chunk.get("jurisdiction") not in ("US", "EU", "GLOBAL"):
            errors.append(f"Chunk {chunk.get('chunk_id')} has invalid jurisdiction: {chunk.get('jurisdiction')}")

    # Validate embeddings match chunk count
    import numpy as np
    embeddings = np.load(str(PROCESSED_DIR / "embeddings.npy"))
    if embeddings.shape[0] != len(chunks):
        errors.append(f"Embedding count {embeddings.shape[0]} != chunk count {len(chunks)}")

    # Validate chunk_index
    with open(PROCESSED_DIR / "chunk_index.json") as f:
        chunk_index = json.load(f)
    if len(chunk_index) != len(chunks):
        errors.append(f"chunk_index has {len(chunk_index)} entries, expected {len(chunks)}")

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    us_chunks = [c for c in chunks if c["jurisdiction"] == "US"]
    eu_chunks = [c for c in chunks if c["jurisdiction"] == "EU"]
    global_chunks = [c for c in chunks if c["jurisdiction"] == "GLOBAL"]

    print("✅ VALIDATION PASSED")
    print(f"   Total chunks : {len(chunks)}")
    print(f"   US chunks    : {len(us_chunks)}")
    print(f"   EU chunks    : {len(eu_chunks)}")
    print(f"   GLOBAL chunks: {len(global_chunks)}")
    print(f"   Embeddings   : {embeddings.shape}")


if __name__ == "__main__":
    main()
