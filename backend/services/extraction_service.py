"""
LexAI Extraction Service
Extracts clean text from PDF and DOCX contracts,
then chunks it for Gemini context window compatibility.
Handles long contracts (30-80 pages) via overlapping chunks.
"""

import io
import re
from dataclasses import dataclass

import pymupdf                        # PyMuPDF
from docx import Document as DocxDoc


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    index:    int
    text:     str
    char_start: int
    char_end:   int


@dataclass
class ExtractionResult:
    full_text:    str
    chunks:       list[Chunk]
    page_count:   int
    word_count:   int
    contract_type: str   # detected heuristically


# ── Constants ─────────────────────────────────────────────────────────────────

CHUNK_SIZE    = 6000    # characters per chunk (~1500 tokens)
CHUNK_OVERLAP = 800     # overlap to preserve clause context across boundaries

CONTRACT_TYPE_KEYWORDS = {
    "NDA":                  ["non-disclosure", "confidentiality agreement", "nda"],
    "SaaS Agreement":       ["software as a service", "saas", "subscription service",
                             "cloud service", "platform license"],
    "Service Agreement":    ["services agreement", "statement of work", "sow",
                             "professional services", "consulting agreement"],
    "Employment Contract":  ["employment agreement", "offer of employment",
                             "terms of employment"],
    "Partnership Agreement":["partnership agreement", "joint venture",
                             "collaboration agreement", "strategic alliance"],
}


# ── Main extraction ───────────────────────────────────────────────────────────

def extract_and_chunk(
    file_bytes: bytes,
    mime_type: str,
) -> ExtractionResult:
    """
    Extract full text from a PDF or DOCX contract,
    then return overlapping chunks for LLM processing.
    """
    if mime_type == "application/pdf":
        full_text, page_count = _extract_pdf(file_bytes)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        full_text, page_count = _extract_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")

    full_text     = _clean_text(full_text)
    word_count    = len(full_text.split())
    contract_type = _detect_contract_type(full_text)
    chunks        = _chunk_text(full_text)

    return ExtractionResult(
        full_text     = full_text,
        chunks        = chunks,
        page_count    = page_count,
        word_count    = word_count,
        contract_type = contract_type,
    )


# ── PDF extraction ────────────────────────────────────────────────────────────

def _extract_pdf(file_bytes: bytes) -> tuple[str, int]:
    doc  = pymupdf.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n\n".join(pages), len(pages)


# ── DOCX extraction ───────────────────────────────────────────────────────────

def _extract_docx(file_bytes: bytes) -> tuple[str, int]:
    doc  = DocxDoc(io.BytesIO(file_bytes))
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    # Estimate page count: ~300 words per page
    word_count = sum(len(p.split()) for p in paras)
    page_count = max(1, word_count // 300)
    return "\n\n".join(paras), page_count


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    # Collapse excessive whitespace / blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    # Remove page numbers (standalone digits on a line)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> list[Chunk]:
    """
    Split text into overlapping chunks.
    Tries to break at paragraph boundaries (double newline) where possible.
    """
    chunks = []
    start  = 0
    index  = 0
    length = len(text)

    while start < length:
        end = min(start + CHUNK_SIZE, length)

        # Try to break at a paragraph boundary within the last 20% of the chunk
        if end < length:
            search_start = start + int(CHUNK_SIZE * 0.8)
            boundary = text.rfind("\n\n", search_start, end)
            if boundary != -1:
                end = boundary

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                index      = index,
                text       = chunk_text,
                char_start = start,
                char_end   = end,
            ))
            index += 1

        # Move forward with overlap
        start = end - CHUNK_OVERLAP if end < length else length

    return chunks


# ── Contract type detection ───────────────────────────────────────────────────

def _detect_contract_type(text: str) -> str:
    text_lower = text[:3000].lower()   # check first 3000 chars only
    for contract_type, keywords in CONTRACT_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return contract_type
    return "Service Agreement"          # safe default
