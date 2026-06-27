"""
run_pipeline.py — QualiTrace AI full live test
Run from Ui-path/: python run_pipeline.py
Requires GROQ_API_KEY in Ui-path/.env
"""
import os, json
os.environ.setdefault(
    "QUALITRACE_KNOWLEDGE_DIR",
    os.path.join(os.path.dirname(__file__), "knowledge", "processed")
)

from backend.app.rag.retriever import retrieve
from backend.app.agents.intake_agent import run_intake
from backend.app.agents.investigation_agent import investigate
from backend.app.agents.capa_agent import generate_capa

complaint = {
    "complaint_type": "contamination",
    "description": "Foreign particle found in tablet bottle",
    "patient_impact": False,
    "recurrence": False,
    "product_type": "finished_pharma",
    "jurisdiction": "US",
}

print("=" * 55)
print("STEP 1 — Intake Agent")
print("=" * 55)
intake_result = run_intake(complaint)
print(json.dumps(intake_result, indent=2))

print("\n" + "=" * 55)
print("STEP 2 — RAG Retrieval")
print("=" * 55)
context = retrieve(complaint)
print("source_list:", context["source_list"])
print("confidence_score:", context["confidence_score"])
print("chunks:", len(context["retrieved_chunks"]))

print("\n" + "=" * 55)
print("STEP 3 — Investigation Agent")
print("=" * 55)
investigation_result = investigate(complaint, context)
print(json.dumps(investigation_result, indent=2))

print("\n" + "=" * 55)
print("STEP 4 — CAPA Agent")
print("=" * 55)
approved_root_cause = investigation_result["root_cause_hypotheses"][0]["hypothesis"]
capa_plan = generate_capa(approved_root_cause, investigation_result, "US", context=context)
print(json.dumps(capa_plan, indent=2))

print("\n✅ Full pipeline complete.")
