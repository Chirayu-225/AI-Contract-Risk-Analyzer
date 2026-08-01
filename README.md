cat > /mnt/user-data/outputs/README.md << 'EOF'
# AI based Contract Risk Analyzer using CUAD-Grounded Taxonomy & Missing-Clause Detection

A full-stack contract risk intelligence platform that extracts and classifies legal clauses from uploaded PDF/DOCX contracts using **Gemini 2.5 Flash**, grounded against the **CUAD (Contract Understanding Atticus Dataset)** legal taxonomy for lawyer-validated risk categorization. The system performs missing-clause detection, aggregates per-party risk exposure, and generates a downloadable structured risk report — deployed end-to-end via **FastAPI**, **React**, and **Docker** on **Railway**.

> Built as a final year B.E. Computer Science project targeting Indian startups and SMEs who sign contracts without proper legal review.

---

## What It Does

Most Indian startups and SMEs sign vendor contracts, SaaS agreements, and NDAs without in-house legal teams. A single overlooked clause — unlimited liability, auto-renewal, IP assignment — can have serious consequences.

This system democratizes contract review by:

- **Flagging risk clauses** grounded in what actual lawyers consider risky (CUAD taxonomy), not keyword heuristics
- **Detecting missing protections** — checks for what *should* be there but isn't (Limitation of Liability, Data Protection, Arbitration clause, etc.)
- **Scoring each party separately** — obligations summarized independently for Party A and Party B
- **Generating a downloadable PDF risk report** — actionable output, not just a chatbot response

---

## Demo

| Upload | Analysis | Report |
|--------|----------|--------|
| Drag and drop PDF or DOCX | 95/100 HIGH RISK score with red flags | Download structured PDF report |

**Test result on a one-sided SaaS MSA:**
- Overall: **95/100 HIGH RISK**
- Flagged: Non-Compete, Auto-Renewal, IP Assignment, Unlimited Client Indemnification
- Missing: Data Protection / DPDP Act 2023, Force Majeure, Arbitration Clause, Warranty / SLA

---

## Features

- **CUAD-Grounded Risk Taxonomy** — 20 clause categories mapped to risk levels (high / medium / low) with plain-language explanations and negotiation recommendations
- **Missing Clause Detection** — checks for 10 standard protections relevant to Indian commercial contracts, with Indian legal context (DPDP Act 2023, Arbitration and Conciliation Act 1996, MSME Act 2006)
- **Per-Party Risk Dashboard** — separate risk scores for Party A and Party B, showing who bears the burden of each clause
- **Multilingual Contract Support** — handles PDF and DOCX formats including mixed-language headers
- **Downloadable PDF Report** — structured risk report with clause breakdown, missing protections table, and legal disclaimer
- **Analysis History** — all past analyses stored and retrievable via SQLite

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite, React Router, Axios, Lucide React |
| Backend | FastAPI (Python 3.11), Uvicorn, Pydantic v2 |
| AI / LLM | Google Gemini 2.5 Flash (free tier API) |
| Document Processing | PyMuPDF (PDF), python-docx (DOCX) |
| Risk Taxonomy | Custom JSON — CUAD-grounded, 20 categories |
| Report Generation | ReportLab |
| Database | SQLite via aiosqlite |
| Deployment | Docker + Railway |

---

## Architecture

```
Browser (React + Vite)
        │  REST
        ▼
FastAPI Backend
   ├── /analyze          → accepts PDF/DOCX upload
   ├── /analyses         → list past analyses
   ├── /analyses/{id}    → fetch single analysis
   └── /analyses/{id}/report → download PDF report
        │
        ├── Extraction Service   (PyMuPDF / python-docx)
        ├── Clause Analysis      (Gemini 2.5 Flash → structured JSON)
        ├── Missing Clause Det.  (Gemini 2.5 Flash → checklist prompt)
        ├── Risk Aggregator      (pure Python — zero API cost)
        └── Report Generator     (ReportLab)
        │
        ▼
     SQLite DB
```

---

## CUAD Taxonomy

Risk categories grounded in the [CUAD dataset](https://www.atticusprojectai.org/cuad) (NeurIPS 2021) — 510 contracts, 13,000+ expert legal annotations:

| Risk Level | Categories |
|-----------|-----------|
| 🔴 High | Unlimited Liability, IP Ownership Assigned, Non-Compete, Auto-Renewal, Termination for Convenience, Indemnification, Liquidated Damages |
| 🟡 Medium | Governing Law, Audit Rights, Exclusivity, Minimum Commitment, Change of Control, Anti-Assignment |
| 🟢 Low | Confidentiality, Limitation of Liability, Warranty, Force Majeure, Dispute Resolution |

---

## Missing Clause Detection

Checks for standard protections relevant to Indian commercial law:

| Clause | Severity | Indian Context |
|--------|----------|----------------|
| Limitation of Liability | Critical | No implied cap under Indian law |
| Data Protection / Privacy | Critical | DPDP Act 2023 obligations |
| Dispute Resolution / Arbitration | High | Litigation averages 3–5 years in India |
| Termination Notice Period | High | Courts may imply "reasonable" notice |
| Warranty / Service Levels | High | No implied SLA in SaaS contracts |
| Force Majeure | Medium | Essential post-COVID |
| Governing Law | Medium | Legal uncertainty without it |
| Payment Terms | Medium | MSME Act 2006 — 45-day rule |

---

## Project Structure

```
lexai/
├── backend/
│   ├── main.py                      # FastAPI app + 4 routes
│   ├── services/
│   │   ├── clause_service.py        # Gemini clause extraction
│   │   ├── extraction_service.py    # PDF/DOCX text extraction
│   │   ├── aggregator_service.py    # Per-party risk scoring
│   │   └── report_service.py        # PDF report generation
│   ├── data/
│   │   └── cuad_taxonomy.json       # CUAD-grounded risk knowledge base
│   ├── db/
│   │   └── database.py              # SQLite layer
│   ├── models/
│   │   └── schemas.py               # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   └── frontend-package/
│       ├── src/
│       │   ├── App.jsx
│       │   ├── pages/
│       │   │   ├── Upload.jsx       # Contract upload + party names
│       │   │   ├── Report.jsx       # Risk dashboard + tabs
│       │   │   └── History.jsx      # Past analyses table
│       │   └── components/
│       │       ├── Sidebar.jsx
│       │       └── ScoreRing.jsx    # Animated SVG score ring
│       └── package.json
├── Dockerfile
├── railway.toml
└── requirements.txt
```

---

## Local Setup

### Prerequisites
- Python 3.11
- Node.js 18+
- A free [Gemini API key](https://aistudio.google.com/app/apikey)

### Backend

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key
set GEMINI_API_KEY=your_key_here       # Windows CMD
$env:GEMINI_API_KEY="your_key_here"   # PowerShell
export GEMINI_API_KEY=your_key_here   # Mac/Linux

# Run the backend
cd backend
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend/frontend-package
npm install
npm run dev
```

Open `http://localhost:5173`

> Both backend (port 8000) and frontend (port 5173) must be running simultaneously.

---

## Docker

```bash
docker build -t lexai .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key lexai
```

---

## Deployment (Railway)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variable: `GEMINI_API_KEY=your_key`
4. Railway auto-detects `railway.toml` and deploys

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Upload contract, get full risk analysis |
| GET | `/analyses` | List all past analyses |
| GET | `/analyses/{id}` | Fetch a specific analysis |
| GET | `/analyses/{id}/report` | Download PDF risk report |

### Example Request

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@contract.pdf" \
  -F "party_a_name=Acme Startup Pvt Ltd" \
  -F "party_b_name=BigVendor Inc"
```

---

## Dataset

- **CUAD** — [atticusprojectai.org/cuad](https://www.atticusprojectai.org/cuad) — 510 commercial contracts, 13,000+ expert annotations (NeurIPS 2021)
- **SEC EDGAR** — Real public company contracts for additional testing
- **CommonPaper.com** — Standardized open-source contracts as balanced baseline

---

## Disclaimer

This tool is for informational purposes only and does not constitute legal advice. Always consult a qualified lawyer before signing any contract. Risk classification is grounded in the CUAD legal taxonomy and Indian commercial law context.

---

## License

MIT License — free to use, modify, and distribute with attribution.
EOF
echo "done"
