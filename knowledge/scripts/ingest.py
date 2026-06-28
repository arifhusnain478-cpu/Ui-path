"""
knowledge/scripts/ingest.py
Reads all PDFs from knowledge/raw/, extracts text, saves to knowledge/processed/raw_docs.json
"""
import json
import os
import sys
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"

JURISDICTION_MAP = {
    "fda_21cfr_211": "US",
    "sop_qa_042_site_a": "US",
    "sop_qa_018_packaging": "US",
    "sop_qa_001_global": "GLOBAL",
    "ich_q9": "GLOBAL",
    "ich_q10": "GLOBAL",
    "ema_eudralex_vol4": "EU",
    "sop_eu_gmp_local": "EU",
}

AUTHORITY_MAP = {
    "fda_21cfr_211": "FDA",
    "sop_qa_042_site_a": "INTERNAL",
    "sop_qa_018_packaging": "INTERNAL",
    "sop_qa_001_global": "INTERNAL",
    "ich_q9": "ICH",
    "ich_q10": "ICH",
    "ema_eudralex_vol4": "EMA",
    "sop_eu_gmp_local": "INTERNAL",
}

DOC_TYPE_MAP = {
    "fda_21cfr_211": "regulation",
    "sop_qa_042_site_a": "sop",
    "sop_qa_018_packaging": "sop",
    "sop_qa_001_global": "sop",
    "ich_q9": "guideline",
    "ich_q10": "guideline",
    "ema_eudralex_vol4": "regulation",
    "sop_eu_gmp_local": "sop",
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        pass

    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.strip()
    except ImportError:
        pass

    raise RuntimeError("No PDF library found. Run: pip install pymupdf")


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(RAW_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"ERROR: No PDF files found in {RAW_DIR}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF files")

    docs = []
    metadata = {}

    for pdf_path in pdf_files:
        doc_id = pdf_path.stem
        print(f"  Processing: {doc_id}...")

        text = extract_text_from_pdf(pdf_path)
        jurisdiction = JURISDICTION_MAP.get(doc_id, "GLOBAL")
        authority = AUTHORITY_MAP.get(doc_id, "INTERNAL")
        doc_type = DOC_TYPE_MAP.get(doc_id, "sop")

        doc = {
            "doc_id": doc_id,
            "filename": pdf_path.name,
            "jurisdiction": jurisdiction,
            "authority": authority,
            "document_type": doc_type,
            "status": "ACTIVE",
            "effective_date": "2020-01-01",
            "expiry_date": None,
            "text": text,
            "char_count": len(text),
        }
        docs.append(doc)
        metadata[doc_id] = {k: v for k, v in doc.items() if k != "text"}
        print(f"    Jurisdiction: {jurisdiction}, chars: {len(text):,}")

    raw_docs_path = PROCESSED_DIR / "raw_docs.json"
    with open(raw_docs_path, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    metadata_path = PROCESSED_DIR / "doc_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Ingested {len(docs)} documents")
    print(f"   raw_docs.json    → {raw_docs_path}")
    print(f"   doc_metadata.json → {metadata_path}")


if __name__ == "__main__":
    main()
