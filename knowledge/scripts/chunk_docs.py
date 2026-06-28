"""
knowledge/scripts/chunk_docs.py
Splits raw_docs.json into 300-400 token chunks. Saves to chunks.json
"""
import json
import re
import sys
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
TARGET_CHUNK_TOKENS = 350
OVERLAP_TOKENS = 50


def approximate_tokens(text: str) -> int:
    return len(text) // 4


def split_into_sentences(text: str) -> list:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text: str, doc_id: str, jurisdiction: str, authority: str, doc_type: str) -> list:
    sentences = split_into_sentences(text)
    chunks = []
    chunk_index = 0
    current_sentences = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = approximate_tokens(sentence)

        if current_tokens + sentence_tokens > TARGET_CHUNK_TOKENS and current_sentences:
            chunk_text_str = " ".join(current_sentences)
            chunks.append({
                "chunk_id": f"{doc_id}_chunk_{chunk_index:03d}",
                "doc_id": doc_id,
                "jurisdiction": jurisdiction,
                "authority": authority,
                "doc_type": doc_type,
                "source": doc_id,
                "section_number": f"{chunk_index + 1}",
                "section_title": f"Section {chunk_index + 1}",
                "text": chunk_text_str,
                "keywords": _extract_keywords(chunk_text_str),
                "status": "ACTIVE",
                "token_count": current_tokens,
            })
            chunk_index += 1
            # Overlap: keep last few sentences
            overlap_sentences = current_sentences[-2:] if len(current_sentences) > 2 else []
            current_sentences = overlap_sentences + [sentence]
            current_tokens = sum(approximate_tokens(s) for s in current_sentences)
        else:
            current_sentences.append(sentence)
            current_tokens += sentence_tokens

    # Last chunk
    if current_sentences:
        chunk_text_str = " ".join(current_sentences)
        chunks.append({
            "chunk_id": f"{doc_id}_chunk_{chunk_index:03d}",
            "doc_id": doc_id,
            "jurisdiction": jurisdiction,
            "authority": authority,
            "doc_type": doc_type,
            "source": doc_id,
            "section_number": f"{chunk_index + 1}",
            "section_title": f"Section {chunk_index + 1}",
            "text": chunk_text_str,
            "keywords": _extract_keywords(chunk_text_str),
            "status": "ACTIVE",
            "token_count": current_tokens,
        })

    return chunks


def _extract_keywords(text: str) -> list:
    pharma_keywords = [
        "contamination", "labeling", "quality", "complaint", "investigation",
        "capa", "batch", "manufacturing", "gmp", "fda", "ema", "ich",
        "recall", "deviation", "validation", "sterility", "packaging",
        "tablet", "capsule", "injectable", "stability", "specification",
        "corrective", "preventive", "risk", "audit", "compliance",
        "regulation", "guideline", "sop", "procedure", "protocol",
    ]
    text_lower = text.lower()
    return [kw for kw in pharma_keywords if kw in text_lower]


def main():
    raw_docs_path = PROCESSED_DIR / "raw_docs.json"
    if not raw_docs_path.exists():
        print(f"ERROR: {raw_docs_path} not found. Run ingest.py first.")
        sys.exit(1)

    with open(raw_docs_path, encoding="utf-8") as f:
        docs = json.load(f)

    all_chunks = []
    for doc in docs:
        doc_chunks = chunk_text(
            text=doc["text"],
            doc_id=doc["doc_id"],
            jurisdiction=doc["jurisdiction"],
            authority=doc["authority"],
            doc_type=doc["document_type"],
        )
        all_chunks.extend(doc_chunks)
        print(f"  {doc['doc_id']}: {len(doc_chunks)} chunks")

    chunks_path = PROCESSED_DIR / "chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Created {len(all_chunks)} chunks → {chunks_path}")


if __name__ == "__main__":
    main()
