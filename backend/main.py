"""
LexAI FastAPI Backend
"""

import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from db.database import init_db, save_analysis, get_analysis, list_analyses
from models.schemas import AnalyzeResponse, AnalysisSummary
from services.extraction_service import extract_and_chunk
from services.clause_service import analyze_clauses, detect_missing_clauses
from services.aggregator_service import aggregate_risks
from services.report_service import generate_report

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="LexAI API",
    description="Contract Risk Intelligence for Indian Startups and SMEs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "LexAI"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_contract(
    file:         UploadFile = File(...),
    party_a_name: str = Form("Party A (You)"),
    party_b_name: str = Form("Party B (Counterparty)"),
):
    """
    Upload a contract PDF or DOCX.
    Returns CUAD-grounded risk flags, missing clause detection,
    per-party risk dashboard, and overall risk score.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not configured")

    mime = file.content_type or ""
    if mime not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Unsupported file type: {mime}. Upload PDF or DOCX."
        )

    file_bytes = await file.read()

    # Phase 1 — Extract text and detect contract type
    extraction = extract_and_chunk(file_bytes, mime)
    if not extraction.full_text.strip():
        raise HTTPException(422, "Could not extract text from the uploaded file.")

    # Phase 2 — Clause analysis (Gemini)
    found_clauses = await analyze_clauses(extraction.full_text, GEMINI_API_KEY)

    # Phase 3 — Missing clause detection (Gemini)
    missing_clauses = await detect_missing_clauses(
        extraction.full_text, extraction.contract_type, GEMINI_API_KEY
    )

    # Phase 4 — Per-party aggregation (pure Python)
    agg = aggregate_risks(
        found_clauses, missing_clauses,
        extraction.contract_type,
        party_a_name, party_b_name,
    )

    # Phase 5 — Persist to SQLite
    analysis_id = await save_analysis(
        filename        = file.filename or "contract",
        contract_type   = extraction.contract_type,
        word_count      = extraction.word_count,
        page_count      = extraction.page_count,
        overall_score   = agg.overall_score,
        risk_summary    = agg.risk_summary,
        red_flags       = agg.red_flags,
        found_clauses   = found_clauses,
        missing_clauses = missing_clauses,
        party_a_name    = agg.party_a.name,
        party_a_score   = agg.party_a.risk_score,
        party_b_name    = agg.party_b.name,
        party_b_score   = agg.party_b.risk_score,
        critical_missing = agg.critical_missing,
    )

    return AnalyzeResponse(
        analysis_id     = analysis_id,
        filename        = file.filename or "contract",
        contract_type   = extraction.contract_type,
        word_count      = extraction.word_count,
        page_count      = extraction.page_count,
        overall_score   = agg.overall_score,
        risk_summary    = agg.risk_summary,
        red_flags       = agg.red_flags,
        found_clauses   = found_clauses,
        missing_clauses = missing_clauses,
        party_a         = asdict(agg.party_a),
        party_b         = asdict(agg.party_b),
        critical_missing = agg.critical_missing,
    )


@app.get("/analyses", response_model=list[AnalysisSummary])
async def get_all_analyses():
    return await list_analyses()


@app.get("/analyses/{analysis_id}", response_model=AnalyzeResponse)
async def get_single_analysis(analysis_id: int):
    record = await get_analysis(analysis_id)
    if not record:
        raise HTTPException(404, "Analysis not found")
    return record


@app.get("/analyses/{analysis_id}/report")
async def download_report(analysis_id: int):
    """Download a PDF risk report for a previously analyzed contract."""
    record = await get_analysis(analysis_id)
    if not record:
        raise HTTPException(404, "Analysis not found")

    # Reconstruct aggregation result for PDF generation
    from services.aggregator_service import AggregationResult, PartyRisk
    agg = AggregationResult(
        party_a = PartyRisk(
            name            = record.get("party_a_name", "Party A"),
            risk_score      = record.get("party_a_score", 0),
            high_risk_count = sum(1 for c in record["found_clauses"]
                                  if c.get("risk_level") == "high"),
            med_risk_count  = sum(1 for c in record["found_clauses"]
                                  if c.get("risk_level") == "medium"),
            low_risk_count  = sum(1 for c in record["found_clauses"]
                                  if c.get("risk_level") == "low"),
            obligations     = [],
            favorable       = [],
        ),
        party_b = PartyRisk(
            name            = record.get("party_b_name", "Party B"),
            risk_score      = record.get("party_b_score", 0),
            high_risk_count = 0,
            med_risk_count  = 0,
            low_risk_count  = 0,
            obligations     = [],
            favorable       = [],
        ),
        overall_score    = record.get("overall_score", 0),
        risk_summary     = record.get("risk_summary", ""),
        red_flags        = record.get("red_flags", []),
        critical_missing = record.get("critical_missing", []),
    )

    pdf_bytes = generate_report(
        result            = agg,
        contract_filename = record.get("filename", "contract"),
        found_clauses     = record.get("found_clauses", []),
        missing_clauses   = record.get("missing_clauses", []),
        contract_type     = record.get("contract_type", "Contract"),
    )

    return Response(
        content      = pdf_bytes,
        media_type   = "application/pdf",
        headers      = {
            "Content-Disposition":
                f'attachment; filename="lexai_report_{analysis_id}.pdf"'
        },
    )
