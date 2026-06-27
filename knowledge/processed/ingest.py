"""
QualiTrace AI — Knowledge Ingestion Pipeline
Runs all 5 stages: extract → chunk → embed → BM25 → validate
Usage: python ingest.py
"""

import os, json, re, pickle, hashlib
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

# ── Paths ──────────────────────────────────────────────────────────────────────
RAW_DIR       = Path(__file__).parent.parent / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ── Document metadata map ──────────────────────────────────────────────────────
DOC_META = {
    "fda_21cfr_211.pdf":      {"jurisdiction": "US",     "authority": "FDA",      "doc_type": "REGULATION", "status": "ACTIVE"},
    "ema_eudralex_vol4.pdf":  {"jurisdiction": "EU",     "authority": "EMA",      "doc_type": "REGULATION", "status": "ACTIVE"},
    "ich_q9.pdf":             {"jurisdiction": "GLOBAL", "authority": "ICH",      "doc_type": "REGULATION", "status": "ACTIVE"},
    "ich_q10.pdf":            {"jurisdiction": "GLOBAL", "authority": "ICH",      "doc_type": "REGULATION", "status": "ACTIVE"},
    "sop_qa_042_site_a.pdf":  {"jurisdiction": "US",     "authority": "INTERNAL", "doc_type": "SOP",        "status": "ACTIVE"},
    "sop_qa_018_packaging.pdf":{"jurisdiction": "US",    "authority": "INTERNAL", "doc_type": "SOP",        "status": "ACTIVE"},
    "sop_qa_001_global.pdf":  {"jurisdiction": "GLOBAL", "authority": "INTERNAL", "doc_type": "SOP",        "status": "ACTIVE"},
    "sop_eu_gmp_local.pdf":   {"jurisdiction": "EU",     "authority": "INTERNAL", "doc_type": "SOP",        "status": "ACTIVE"},
}

# ── Stage 1: Extract text from PDFs ───────────────────────────────────────────
def extract_texts():
    print("\n[Stage 1] Extracting text from PDFs...")
    docs = []
    for filename, meta in DOC_META.items():
        pdf_path = RAW_DIR / filename
        if not pdf_path.exists():
            print(f"  ✗ MISSING: {filename}")
            continue
        doc = fitz.open(str(pdf_path))
        pages = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": page_num + 1, "text": text})
        doc.close()
        full_text = "\n".join(p["text"] for p in pages)
        doc_id = filename.replace(".pdf", "")
        docs.append({
            "doc_id": doc_id,
            "filename": filename,
            "jurisdiction": meta["jurisdiction"],
            "authority": meta["authority"],
            "doc_type": meta["doc_type"],
            "status": meta["status"],
            "effective_date": "2024-01-01",
            "expiry_date": None,
            "full_text": full_text,
            "page_count": len(pages),
        })
        print(f"  ✓ {filename} — {len(pages)} pages, {len(full_text):,} chars")
    print(f"  Extracted {len(docs)}/8 documents")
    return docs

# ── Stage 2: Chunk documents ──────────────────────────────────────────────────
def chunk_docs(docs):
    print("\n[Stage 2] Chunking documents...")
    TARGET_TOKENS = 350
    WORDS_PER_TOKEN = 0.75  # approx
    TARGET_WORDS = int(TARGET_TOKENS / WORDS_PER_TOKEN)

    all_chunks = []
    doc_metadata = {}

    for doc in docs:
        doc_id = doc["doc_id"]
        text = doc["full_text"]

        # Split into sentences (simple but effective)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        chunks = []
        current_words = []
        current_sentences = []

        for sentence in sentences:
            words = sentence.split()
            if len(current_words) + len(words) > TARGET_WORDS and current_words:
                # Save current chunk
                chunk_text = " ".join(current_sentences)
                chunk_id = f"{doc_id}_chunk_{len(chunks):04d}"
                # Extract keywords (capitalized/important words)
                keywords = list(set(
                    w.lower() for w in chunk_text.split()
                    if len(w) > 5 and w[0].isupper()
                ))[:10]
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "jurisdiction": doc["jurisdiction"],
                    "authority": doc["authority"],
                    "doc_type": doc["doc_type"],
                    "status": doc["status"],
                    "section_number": str(len(chunks) + 1),
                    "section_title": f"{doc_id} — Section {len(chunks) + 1}",
                    "text": chunk_text,
                    "keywords": keywords,
                    "word_count": len(current_words),
                })
                current_words = []
                current_sentences = []
            current_words.extend(words)
            current_sentences.append(sentence)

        # Flush remaining
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunk_id = f"{doc_id}_chunk_{len(chunks):04d}"
            keywords = list(set(
                w.lower() for w in chunk_text.split()
                if len(w) > 5 and w[0].isupper()
            ))[:10]
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "jurisdiction": doc["jurisdiction"],
                "authority": doc["authority"],
                "doc_type": doc["doc_type"],
                "status": doc["status"],
                "section_number": str(len(chunks) + 1),
                "section_title": f"{doc_id} — Section {len(chunks) + 1}",
                "text": chunk_text,
                "keywords": keywords,
                "word_count": len(chunk_text.split()),
            })

        all_chunks.extend(chunks)
        doc_metadata[doc_id] = {
            "doc_id": doc_id,
            "filename": doc["filename"],
            "jurisdiction": doc["jurisdiction"],
            "authority": doc["authority"],
            "doc_type": doc["doc_type"],
            "status": doc["status"],
            "effective_date": doc["effective_date"],
            "expiry_date": doc["expiry_date"],
            "chunk_count": len(chunks),
        }
        print(f"  ✓ {doc_id} → {len(chunks)} chunks")

    # Save
    chunks_path = PROCESSED_DIR / "chunks.json"
    with open(chunks_path, "w") as f:
        json.dump(all_chunks, f, indent=2)

    meta_path = PROCESSED_DIR / "doc_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(doc_metadata, f, indent=2)

    print(f"  Total chunks: {len(all_chunks)}")
    return all_chunks

# ── Stage 3: Embed chunks ─────────────────────────────────────────────────────
def embed_chunks(chunks):
    print("\n[Stage 3] Embedding chunks with TF-IDF + SVD (local, no internet)...")
    texts = [c["text"] for c in chunks]
    print(f"  Vectorizing {len(texts)} chunks...")

    # TF-IDF → 384-dim dense vectors via SVD (mimics sentence embedding output shape)
    n_components = min(384, len(texts) - 1)
    vectorizer = TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        strip_accents="unicode",
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    embeddings = svd.fit_transform(tfidf_matrix)
    embeddings = normalize(embeddings)  # L2 normalize like sentence-transformers

    # Pad to 384 dims if needed
    if embeddings.shape[1] < 384:
        pad = np.zeros((embeddings.shape[0], 384 - embeddings.shape[1]))
        embeddings = np.hstack([embeddings, pad])

    embeddings = embeddings.astype(np.float32)
    np.save(str(PROCESSED_DIR / "embeddings.npy"), embeddings)

    # Save vectorizer + SVD for runtime use
    with open(PROCESSED_DIR / "tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(PROCESSED_DIR / "svd_model.pkl", "wb") as f:
        pickle.dump(svd, f)

    # Save index mapping: position → chunk_id
    chunk_index = {i: c["chunk_id"] for i, c in enumerate(chunks)}
    with open(PROCESSED_DIR / "chunk_index.json", "w") as f:
        json.dump(chunk_index, f, indent=2)

    print(f"  ✓ Saved embeddings.npy — shape {embeddings.shape}")
    return embeddings

# ── Stage 4: Build BM25 index ─────────────────────────────────────────────────
def build_bm25(chunks):
    print("\n[Stage 4] Building BM25 index...")
    tokenized = []
    for c in chunks:
        tokens = (c["text"] + " " + " ".join(c["keywords"])).lower().split()
        tokenized.append(tokens)

    bm25 = BM25Okapi(tokenized)
    with open(PROCESSED_DIR / "bm25_index.pkl", "wb") as f:
        pickle.dump(bm25, f)

    print(f"  ✓ BM25 index built over {len(tokenized)} chunks")
    return bm25

# ── Stage 5: Validate ─────────────────────────────────────────────────────────
def validate():
    print("\n[Stage 5] Validating processed files...")
    errors = []

    # Load chunks
    chunks_path = PROCESSED_DIR / "chunks.json"
    if not chunks_path.exists():
        errors.append("chunks.json missing")
    else:
        with open(chunks_path) as f:
            chunks = json.load(f)
        required_fields = {"chunk_id", "doc_id", "jurisdiction", "doc_type", "status", "text", "keywords"}
        for i, c in enumerate(chunks):
            missing = required_fields - set(c.keys())
            if missing:
                errors.append(f"Chunk {i} missing fields: {missing}")
            if c.get("jurisdiction") not in ("US", "EU", "GLOBAL"):
                errors.append(f"Chunk {i} invalid jurisdiction: {c.get('jurisdiction')}")
            if c.get("status") == "SUPERSEDED":
                errors.append(f"Chunk {i} is SUPERSEDED and should not be active")
        print(f"  chunks.json: {len(chunks)} chunks ✓")

    # Load embeddings
    emb_path = PROCESSED_DIR / "embeddings.npy"
    if not emb_path.exists():
        errors.append("embeddings.npy missing")
    else:
        emb = np.load(str(emb_path))
        if len(chunks) != emb.shape[0]:
            errors.append(f"Embedding count {emb.shape[0]} != chunk count {len(chunks)}")
        else:
            print(f"  embeddings.npy: shape {emb.shape} ✓")

    # Load BM25
    bm25_path = PROCESSED_DIR / "bm25_index.pkl"
    if not bm25_path.exists():
        errors.append("bm25_index.pkl missing")
    else:
        print(f"  bm25_index.pkl: exists ✓")

    # Check embedding models
    for fname in ["tfidf_vectorizer.pkl", "svd_model.pkl"]:
        if not (PROCESSED_DIR / fname).exists():
            errors.append(f"{fname} missing")
        else:
            print(f"  {fname}: exists ✓")

    # Load doc metadata
    meta_path = PROCESSED_DIR / "doc_metadata.json"
    if not meta_path.exists():
        errors.append("doc_metadata.json missing")
    else:
        with open(meta_path) as f:
            meta = json.load(f)
        print(f"  doc_metadata.json: {len(meta)} documents ✓")

    # Load chunk_index
    idx_path = PROCESSED_DIR / "chunk_index.json"
    if not idx_path.exists():
        errors.append("chunk_index.json missing")
    else:
        print(f"  chunk_index.json: exists ✓")

    if errors:
        print(f"\n  ✗ VALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
        return False
    else:
        print(f"\n  ✅ VALIDATION PASSED — all files correct")
        return True

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("QualiTrace AI — Knowledge Ingestion Pipeline")
    print("=" * 60)

    docs    = extract_texts()
    chunks  = chunk_docs(docs)
    embeds  = embed_chunks(chunks)
    bm25    = build_bm25(chunks)
    passed  = validate()

    print("\n" + "=" * 60)
    if passed:
        print("✅ Pipeline complete. Ready for RAG.")
    else:
        print("✗ Pipeline completed with errors. Fix before building agents.")
    print("=" * 60)
