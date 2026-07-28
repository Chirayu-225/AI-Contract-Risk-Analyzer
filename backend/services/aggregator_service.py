"""
LexAI Per-Party Risk Aggregator
Pure Python — zero API calls.
Splits identified clauses and risks between the two contracting parties,
computes risk scores, and generates a structured dashboard payload.
"""

from dataclasses import dataclass, field


@dataclass
class PartyRisk:
    name:            str
    risk_score:      int          # 0–100
    high_risk_count: int
    med_risk_count:  int
    low_risk_count:  int
    obligations:     list[dict]   # clauses where this party bears the burden
    favorable:       list[dict]   # clauses that favor this party


@dataclass
class AggregationResult:
    party_a:         PartyRisk
    party_b:         PartyRisk
    overall_score:   int          # 0–100, higher = riskier for the uploader
    risk_summary:    str
    red_flags:       list[str]    # top critical issues in plain language
    critical_missing: list[dict]  # missing clauses with severity = critical


# ── Risk weights ──────────────────────────────────────────────────────────────

RISK_WEIGHTS = {"high": 20, "medium": 8, "low": 2}
MAX_SCORE    = 100


def aggregate_risks(
    found_clauses:   list[dict],
    missing_clauses: list[dict],
    contract_type:   str,
    party_a_name:    str = "Party A (You)",
    party_b_name:    str = "Party B (Counterparty)",
) -> AggregationResult:
    """
    Given found clauses and missing clauses, build per-party risk profiles
    and an overall risk score for the uploading party.
    """
    party_a_obligations = []
    party_a_favorable   = []
    party_b_obligations = []
    party_b_favorable   = []

    a_score = 0
    b_score = 0

    for clause in found_clauses:
        risk_level  = clause.get("risk_level", "medium")
        party_bias  = clause.get("party_bias", "neutral")
        burdened    = clause.get("party_burdened", "Unclear")
        weight      = RISK_WEIGHTS.get(risk_level, 5)

        # Determine who bears the burden
        if burdened in ("Party A", "Both") or party_bias == "vendor-favored":
            party_a_obligations.append(clause)
            a_score += weight
        elif burdened == "Party B":
            party_b_obligations.append(clause)
            b_score += weight

        # Determine who benefits
        if party_bias == "buyer-favored":
            party_a_favorable.append(clause)
        elif party_bias == "vendor-favored":
            party_b_favorable.append(clause)

    # Missing clauses add to party A's risk (they are unprotected)
    missing_score = sum(
        RISK_WEIGHTS.get(m.get("severity", "medium"), 5)
        for m in missing_clauses
    )
    a_score += missing_score

    # Normalize to 0-100
    a_normalized = min(MAX_SCORE, a_score)
    b_normalized = min(MAX_SCORE, b_score)

    party_a = PartyRisk(
        name            = party_a_name,
        risk_score      = a_normalized,
        high_risk_count = sum(1 for c in party_a_obligations if c.get("risk_level") == "high"),
        med_risk_count  = sum(1 for c in party_a_obligations if c.get("risk_level") == "medium"),
        low_risk_count  = sum(1 for c in party_a_obligations if c.get("risk_level") == "low"),
        obligations     = party_a_obligations,
        favorable       = party_a_favorable,
    )
    party_b = PartyRisk(
        name            = party_b_name,
        risk_score      = b_normalized,
        high_risk_count = sum(1 for c in party_b_obligations if c.get("risk_level") == "high"),
        med_risk_count  = sum(1 for c in party_b_obligations if c.get("risk_level") == "medium"),
        low_risk_count  = sum(1 for c in party_b_obligations if c.get("risk_level") == "low"),
        obligations     = party_b_obligations,
        favorable       = party_b_favorable,
    )

    overall_score   = a_normalized
    risk_summary    = _build_summary(party_a, party_b, missing_clauses, contract_type)
    red_flags       = _build_red_flags(found_clauses, missing_clauses)
    critical_missing = [m for m in missing_clauses if m.get("severity") == "critical"]

    return AggregationResult(
        party_a          = party_a,
        party_b          = party_b,
        overall_score    = overall_score,
        risk_summary     = risk_summary,
        red_flags        = red_flags,
        critical_missing = critical_missing,
    )


def _build_summary(
    party_a: PartyRisk,
    party_b: PartyRisk,
    missing: list[dict],
    contract_type: str,
) -> str:
    score = party_a.risk_score
    if score >= 70:
        level = "HIGH RISK"
        advice = "This contract is heavily skewed against you. Do not sign without legal review."
    elif score >= 40:
        level = "MEDIUM RISK"
        advice = "This contract has notable risks. Negotiate the flagged clauses before signing."
    else:
        level = "LOW RISK"
        advice = "This contract appears relatively balanced. Review flagged items as a precaution."

    missing_count = len(missing)
    critical_count = sum(1 for m in missing if m.get("severity") == "critical")

    summary = (
        f"Overall Risk Level: {level} (Score: {score}/100). "
        f"{advice} "
        f"Found {party_a.high_risk_count} high-risk clause(s) burdening you"
        + (f" and {missing_count} missing standard protection(s)" if missing_count else "")
        + (f", including {critical_count} critical gap(s)" if critical_count else "")
        + f". Contract type detected: {contract_type}."
    )
    return summary


def _build_red_flags(
    found_clauses: list[dict],
    missing_clauses: list[dict],
) -> list[str]:
    flags = []

    # High-risk found clauses
    for clause in found_clauses:
        if clause.get("risk_level") == "high":
            plain = clause.get("plain_language") or clause.get("raw_risk_signal", "")
            if plain:
                flags.append(f"⚠ {clause['category']}: {plain}")

    # Critical missing clauses
    for m in missing_clauses:
        if m.get("severity") == "critical":
            flags.append(f"🚫 MISSING — {m['clause']}: {m['reason']}")

    return flags[:8]   # cap at 8 for UI readability
