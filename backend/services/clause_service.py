"""
LexAI Clause Analysis Service - Fixed JSON parsing for truncated responses
"""

import json
import re
import asyncio
import httpx
from pathlib import Path

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

_TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "cuad_taxonomy.json"
with open(_TAXONOMY_PATH, encoding="utf-8") as f:
    _TAXONOMY = json.load(f)

RISK_CATEGORIES = list(_TAXONOMY["risk_categories"].keys())

EXTRACTION_PROMPT = """You are a legal contract risk analyst. Your job is to identify risky clauses in contracts.

Analyze the contract below and identify ALL clauses that match ANY of these risk categories:

{categories}

IMPORTANT INSTRUCTIONS:
- Be thorough. If a clause is related to a category, include it.
- Auto-renewal or automatic renewal clauses -> flag as "Auto-Renewal"
- IP assignment, work product ownership -> flag as "IP Ownership Assigned"
- Non-compete, non-solicitation, restrictive covenants -> flag as "Non-Compete"
- Indemnification, hold harmless -> flag as "Indemnification"
- Termination for convenience, termination without cause -> flag as "Termination for Convenience"
- Liability caps, unlimited liability, damage exclusions -> flag as "Unlimited Liability" or "Limitation of Liability"
- Minimum spend, minimum purchase commitments -> flag as "Minimum Commitment"
- Exclusive jurisdiction, governing law -> flag as "Governing Law"
- Audit rights, inspection rights -> flag as "Audit Rights"
- Assignment restrictions -> flag as "Anti-Assignment"
- Liquidated damages, penalty clauses -> flag as "Liquidated Damages"
- Confidentiality, NDA provisions -> flag as "Confidentiality"
- Warranty provisions -> flag as "Warranty"
- Dispute resolution, arbitration -> flag as "Dispute Resolution"
- Force majeure -> flag as "Force Majeure"

Return ONLY a valid JSON array, no markdown, no preamble, no explanation.

Each element must have exactly these fields:
[
  {{
    "category": "<category name from the list above>",
    "found": true,
    "excerpt": "<direct quote from contract, max 100 chars>",
    "party_burdened": "<Party A | Party B | Both | Unclear>",
    "raw_risk_signal": "<one sentence max>"
  }}
]

IMPORTANT: Keep excerpts under 100 characters. Keep raw_risk_signal to one short sentence.
This ensures the full JSON fits within token limits.

Return [] ONLY if the contract contains absolutely none of the listed clause types.

CONTRACT TEXT:
{contract_text}
"""

MISSING_CLAUSE_PROMPT = """You are a contract review expert specializing in Indian commercial law.
Review the contract text below and determine which standard protective clauses
are ABSENT from this contract.

Check for the presence of each clause in this list:
{checklist}

Return ONLY a valid JSON array, no markdown, no preamble, no explanation.

For each clause that is MISSING from the contract, include:
[
  {{
    "clause": "<clause name>",
    "severity": "<critical | high | medium>",
    "reason": "<one sentence why it matters>",
    "indian_context": "<one sentence Indian legal context>"
  }}
]

Keep reason and indian_context to one short sentence each.
Only include clauses that are genuinely ABSENT. If all clauses are present, return [].

CONTRACT TEXT:
{contract_text}
"""


async def analyze_clauses(contract_text: str, api_key: str) -> list[dict]:
    categories_str = "\n".join(f"- {c}" for c in RISK_CATEGORIES)
    text_for_prompt = contract_text[:700_000]

    prompt = EXTRACTION_PROMPT.format(
        categories=categories_str,
        contract_text=text_for_prompt,
    )

    raw = await _call_gemini(prompt, api_key, temperature=0.1, max_tokens=8192)

    print("\n=== GEMINI CLAUSE RESPONSE (first 1500 chars) ===")
    print(raw[:1500])
    print("=== END ===\n", flush=True)

    clauses = _parse_json_robust(raw)
    print(f"Parsed {len(clauses)} clauses", flush=True)

    enriched = []
    for clause in clauses:
        category = clause.get("category", "")
        meta = _TAXONOMY["risk_categories"].get(category, {})
        enriched.append({
            **clause,
            "risk_level":     meta.get("risk_level", "medium"),
            "party_bias":     meta.get("party_bias", "neutral"),
            "description":    meta.get("description", ""),
            "plain_language": meta.get("plain_language", ""),
            "recommendation": meta.get("recommendation", ""),
            "cuad_label":     meta.get("cuad_label", category),
        })

    return enriched


async def detect_missing_clauses(contract_text: str, contract_type: str, api_key: str) -> list[dict]:
    full_checklist = _TAXONOMY["missing_clause_checklist"]
    relevant_clauses = _TAXONOMY["contract_types"].get(
        contract_type, [c["clause"] for c in full_checklist]
    )
    filtered = [c for c in full_checklist if c["clause"] in relevant_clauses]
    checklist_str = "\n".join(f"- {c['clause']} (severity: {c['severity']})" for c in filtered)

    text_for_prompt = contract_text[:700_000]
    prompt = MISSING_CLAUSE_PROMPT.format(
        checklist=checklist_str,
        contract_text=text_for_prompt,
    )

    raw = await _call_gemini(prompt, api_key, temperature=0.1, max_tokens=4096)

    print("\n=== GEMINI MISSING CLAUSE RESPONSE ===")
    print(raw[:800])
    print("=== END ===\n", flush=True)

    missing = _parse_json_robust(raw)
    print(f"Parsed {len(missing)} missing clauses", flush=True)

    checklist_map = {c["clause"]: c for c in full_checklist}
    enriched = []
    for item in missing:
        clause_name = item.get("clause", "")
        meta = checklist_map.get(clause_name, {})
        enriched.append({
            "clause":         clause_name,
            "severity":       item.get("severity") or meta.get("severity", "medium"),
            "reason":         item.get("reason") or meta.get("reason", ""),
            "indian_context": item.get("indian_context") or meta.get("indian_context", ""),
        })

    return enriched


async def _call_gemini(prompt: str, api_key: str, temperature: float = 0.2,
                       max_tokens: int = 8192, max_retries: int = 3) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{GEMINI_API_URL}?key={api_key}", json=payload,
                )
                if response.status_code in (503, 429) and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                response.raise_for_status()

            data = response.json()

            # Check for finish reason — if STOP, response is complete
            # If MAX_TOKENS, it was cut off mid-JSON
            candidate = data.get("candidates", [{}])[0]
            finish_reason = candidate.get("finishReason", "STOP")
            text = (
                candidate.get("content", {})
                .get("parts", [{}])[0]
                .get("text", "[]")
            )
            print(f"Gemini finish reason: {finish_reason}, response length: {len(text)}", flush=True)
            return text

        except httpx.HTTPStatusError as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise

    if last_error:
        raise last_error
    return "[]"


def _parse_json_robust(raw: str) -> list[dict]:
    """
    Robust JSON parser that handles:
    - Markdown code fences (```json ... ```)
    - Truncated responses (incomplete JSON arrays)
    - Extra text before/after the JSON
    """
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    # Try direct parse first
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try to extract JSON array with regex
    match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Response was truncated — extract complete objects manually
    # Find all complete {...} objects within the array
    results = []
    for obj_match in re.finditer(r'\{[^{}]*\}', cleaned, re.DOTALL):
        try:
            obj = json.loads(obj_match.group())
            if isinstance(obj, dict) and "category" in obj or "clause" in obj:
                results.append(obj)
        except json.JSONDecodeError:
            continue

    if results:
        print(f"Recovered {len(results)} objects from truncated response", flush=True)
        return results

    return []
