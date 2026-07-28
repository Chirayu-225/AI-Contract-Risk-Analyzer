"""
LexAI Database Layer — SQLite via aiosqlite
"""

import json
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "lexai.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                filename         TEXT NOT NULL,
                contract_type    TEXT,
                word_count       INTEGER,
                page_count       INTEGER,
                overall_score    INTEGER,
                risk_summary     TEXT,
                red_flags        TEXT,
                found_clauses    TEXT,
                missing_clauses  TEXT,
                party_a_name     TEXT,
                party_a_score    INTEGER,
                party_b_name     TEXT,
                party_b_score    INTEGER,
                critical_missing TEXT,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def save_analysis(
    filename: str,
    contract_type: str,
    word_count: int,
    page_count: int,
    overall_score: int,
    risk_summary: str,
    red_flags: list,
    found_clauses: list,
    missing_clauses: list,
    party_a_name: str,
    party_a_score: int,
    party_b_name: str,
    party_b_score: int,
    critical_missing: list,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO analyses (
                filename, contract_type, word_count, page_count,
                overall_score, risk_summary, red_flags,
                found_clauses, missing_clauses,
                party_a_name, party_a_score,
                party_b_name, party_b_score, critical_missing
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                filename, contract_type, word_count, page_count,
                overall_score, risk_summary,
                json.dumps(red_flags),
                json.dumps(found_clauses),
                json.dumps(missing_clauses),
                party_a_name, party_a_score,
                party_b_name, party_b_score,
                json.dumps(critical_missing),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_analysis(analysis_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        ) as cur:
            row = await cur.fetchone()
            return _deserialize(dict(row)) if row else None


async def list_analyses() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, filename, contract_type, overall_score,
                      party_a_name, party_a_score, created_at
               FROM analyses ORDER BY created_at DESC"""
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


def _deserialize(row: dict) -> dict:
    for field in ("red_flags", "found_clauses", "missing_clauses", "critical_missing"):
        if row.get(field):
            try:
                row[field] = json.loads(row[field])
            except Exception:
                row[field] = []
    return row
