# QualiTrace AI
**Team: QualiBots | UiPath AgentHack 2026**

## 📖 Project Description
**The Problem:** Traditional quality assurance in the pharmaceutical manufacturing industry is heavily bottlenecked. Manual triage of critical complaints (e.g., contamination, labeling errors) means high-risk alerts can get buried in inboxes, delaying corrective actions and putting regulatory compliance and patient safety at risk.

**What it does:** QualiTrace AI is an autonomous, end-to-end Agentic AI pipeline for pharma complaint triage and emergency escalation. When a complaint is submitted, the system automatically:
1. Classifies the risk level (critical/high/medium/low).
2. Investigates the issue using a Hybrid RAG pipeline against actual FDA 21 CFR regulations and internal SOPs.
3. Generates ranked root cause hypotheses and a full CAPA (Corrective and Preventive Action) plan.
4. Routes the data through a 7-stage workflow with strict SLA enforcement.

## 🤖 UiPath Components
This solution heavily leverages the UiPath ecosystem to orchestrate the AI pipeline:
* **UiPath Maestro:** Used to orchestrate the overarching 7-stage case management workflow (Intake → Risk Assessment → Auto Investigation → Human Review → CAPA → Effectiveness Review → Closure), enforcing SLA deadlines based on risk level.
* **UiPath Studio (Desktop):** Utilizes custom-coded workflows (including injected VB.NET `Invoke Code` blocks) to bypass standard UI bottlenecks, handle robust data extraction via Regex, execute API payloads to our backend, and dispatch styled HTML emergency alerts via raw SMTP.
* **UiPath Orchestrator:** Hosts and manages the Maestro deployments and local bot connectivity.

## 🧠 Agent Type
**This solution utilizes BOTH Coded Agents and Low-code Agents.**
* **Coded Agents:** The core intelligence runs on a Python/FastAPI backend utilizing a custom architecture of three chained AI Agents (Intake, Investigation, and CAPA) powered by Groq's `llama-3.3-70b-versatile` model. 
* **Low-code Agents/Orchestration:** The cognitive output of the coded agents is seamlessly routed into UiPath Maestro's low-code orchestration environment for human-in-the-loop review and SLA management.

## ⚙️ Setup Instructions for Judging

### 1. Backend (Python/FastAPI)
1. Clone the repository and navigate to the `/backend` directory.
2. Create and activate a virtual environment: `python -m venv .venv` followed by `.\.venv\Scripts\Activate.ps1` (Windows).
3. Install dependencies: `pip install -r requirements.txt`.
4. Ensure your Groq API key is set in your `.env` file.
5. Run the server: `uvicorn app.main:app --reload`. The server will run on `http://127.0.0.1:8000`.

### 2. Frontend (React/Vite)
1. Navigate to the `/frontend` directory.
2. Install Node dependencies: `npm install`.
3. Start the development server: `npm run dev`.
4. The dashboard will be accessible via localhost. All HTTP requests are routed via Axios to the local backend. 

### 3. UiPath Automation
1. Open the project folder in **UiPath Studio**.
2. Open `NotificationSender.xaml`.
3. In the Variables panel, locate the `GmailAppPassword` variable.
4. Replace the default string with a valid 16-letter Gmail App Password for SMTP dispatch.
5. Ensure the backend is running, then click **Debug File** to test the extraction and email dispatch pipeline.
