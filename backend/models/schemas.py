"""LexAI Pydantic Schemas"""

from pydantic import BaseModel
from typing import Optional


class FoundClause(BaseModel):
    category:       str
    found:          bool = True
    excerpt:        str
    party_burdened: str
    raw_risk_signal: str
    risk_level:     str
    party_bias:     str
    description:    str
    plain_language: str
    recommendation: str
    cuad_label:     str


class MissingClause(BaseModel):
    clause:         str
    severity:       str
    reason:         str
    indian_context: str


class PartyRiskOut(BaseModel):
    name:            str
    risk_score:      int
    high_risk_count: int
    med_risk_count:  int
    low_risk_count:  int


class AnalyzeResponse(BaseModel):
    analysis_id:     int
    filename:        str
    contract_type:   str
    word_count:      int
    page_count:      int
    overall_score:   int
    risk_summary:    str
    red_flags:       list[str]
    found_clauses:   list[dict]
    missing_clauses: list[dict]
    party_a:         PartyRiskOut
    party_b:         PartyRiskOut
    critical_missing: list[dict]


class AnalysisSummary(BaseModel):
    id:            int
    filename:      str
    contract_type: Optional[str]
    overall_score: Optional[int]
    party_a_name:  Optional[str]
    party_a_score: Optional[int]
    created_at:    str
