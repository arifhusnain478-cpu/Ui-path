"""
knowledge/scripts/embed_chunks.py
Creates TF-IDF + SVD embeddings for all chunks. Saves embeddings.npy and chunk_index.json
"""
import json
import sys
import numpy as np
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
N_COMPONENTS = 74


def main():
    chunks_path = PROCESSED_DIR / "chunks.json"
    if not chunks_path.exists():
        print(f"ERROR: {chunks_path} not found. Run chunk_docs.py first.")
        sys.exit(1)

    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Embedding {len(chunks)} chunks with TF-IDF + SVD (n={N_COMPONENTS})...")

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize
    except ImportError:
        print("ERROR: scikit-learn not installed. Run: pip install scikit-learn")
        sys.exit(1)

    texts = [c["text"] for c in chunks]
    chunk_ids = [c["chunk_id"] for c in chunks]

    n_components = min(N_COMPONENTS, len(texts) - 1)

    vectorizer = TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    svd = TruncatedSVD(n_components=n_components, random_state=42)
    embeddings = svd.fit_transform(tfidf_matrix)
    embeddings = normalize(embeddings, norm="l2")

    embeddings_path = PROCESSED_DIR / "embeddings.npy"
    np.save(str(embeddings_path), embeddings)

    chunk_index = {chunk_id: idx for idx, chunk_id in enumerate(chunk_ids)}
    chunk_index_path = PROCESSED_DIR / "chunk_index.json"
    with open(chunk_index_path, "w") as f:
        json.dump(chunk_index, f, indent=2)

    import pickle
    vectorizer_path = PROCESSED_DIR / "tfidf_vectorizer.pkl"
    svd_path = PROCESSED_DIR / "svd_model.pkl"
    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)
    with open(svd_path, "wb") as f:
        pickle.dump(svd, f)

    print(f"✅ Embeddings shape: {embeddings.shape}")
    print(f"   embeddings.npy    → {embeddings_path}")
    print(f"   chunk_index.json  → {chunk_index_path}")
    print(f"   tfidf_vectorizer.pkl saved")
    print(f"   svd_model.pkl saved")


if __name__ == "__main__":
    main()
