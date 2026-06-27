"""
build_knowledge.py
Run once from Ui-path/ to produce all RAG artefacts that the rag/ modules expect:
  knowledge/processed/
    chunk_index.json      — { "0": chunk_id, "1": chunk_id, … }
    embeddings.npy        — float32 array (N, 384) — TF-IDF + SVD + L2-norm
    tfidf_vectorizer.pkl  — fitted TfidfVectorizer
    svd_model.pkl         — fitted TruncatedSVD
    bm25_index.pkl        — fitted BM25Okapi
"""

import json
import pickle
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from rank_bm25 import BM25Okapi

PROCESSED = Path("knowledge/processed")

# ── 1. Load chunks ──────────────────────────────────────────────────────────
with open(PROCESSED / "chunks.json") as f:
    chunks = json.load(f)

texts      = [c["text"] for c in chunks]
chunk_ids  = [c["chunk_id"] for c in chunks]
N          = len(chunks)
print(f"Loaded {N} chunks.")

# ── 2. chunk_index.json ─────────────────────────────────────────────────────
chunk_index = {str(i): cid for i, cid in enumerate(chunk_ids)}
with open(PROCESSED / "chunk_index.json", "w") as f:
    json.dump(chunk_index, f, indent=2)
print("✅ chunk_index.json written")

# ── 3. TF-IDF vectorizer ────────────────────────────────────────────────────
vectorizer = TfidfVectorizer(
    max_features=5000,
    sublinear_tf=True,
    stop_words="english",
)
tfidf_matrix = vectorizer.fit_transform(texts)   # shape (N, vocab)
with open(PROCESSED / "tfidf_vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)
print("✅ tfidf_vectorizer.pkl written")

# ── 4. SVD → 384-dim embeddings ─────────────────────────────────────────────
n_components = min(384, N - 1, tfidf_matrix.shape[1] - 1)
svd = TruncatedSVD(n_components=n_components, random_state=42)
svd_matrix = svd.fit_transform(tfidf_matrix)     # shape (N, n_components)
with open(PROCESSED / "svd_model.pkl", "wb") as f:
    pickle.dump(svd, f)
print(f"✅ svd_model.pkl written  (n_components={n_components})")

# Pad to exactly 384 if SVD produced fewer components (small corpus)
if svd_matrix.shape[1] < 384:
    pad = np.zeros((N, 384 - svd_matrix.shape[1]), dtype=np.float32)
    svd_matrix = np.hstack([svd_matrix, pad])

embeddings = normalize(svd_matrix).astype(np.float32)  # L2-normalise → cosine = dot
np.save(str(PROCESSED / "embeddings.npy"), embeddings)
print(f"✅ embeddings.npy written  shape={embeddings.shape}")

# ── 5. BM25 index ───────────────────────────────────────────────────────────
tokenized_corpus = [t.lower().split() for t in texts]
bm25 = BM25Okapi(tokenized_corpus)
with open(PROCESSED / "bm25_index.pkl", "wb") as f:
    pickle.dump(bm25, f)
print("✅ bm25_index.pkl written")

print("\nAll knowledge artefacts built successfully.")
