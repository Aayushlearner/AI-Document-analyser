"""
Document Processor
------------------
Extracts raw text from uploaded files and splits into chunks.

Supported formats:
  - PDF  (via PyMuPDF / fitz)
  - TXT  (plain read)
  - DOCX (via python-docx)
  - CSV / XLSX (via pandas — converted to readable text rows)

Chunking strategy:
  - Sliding window over sentences with ~500-token target size and 50-token overlap.
  - Each chunk keeps metadata: source filename, page number, chunk index.
"""

import os
import re
import logging
import fitz  # PyMuPDF
import pandas as pd
from docx import Document as DocxDocument
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHUNK_SIZE = 500        # approximate characters per chunk
CHUNK_OVERLAP = 80      # characters of overlap between consecutive chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_and_chunk(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    Given a saved file path and original filename, return a list of chunk dicts:
    {
        "content": str,
        "page_number": int | None,
        "chunk_index": int,
        "filename": str,
    }
    """
    ext = os.path.splitext(filename)[1].lower()
    logger.info("Extracting text from '%s' (type=%s)", filename, ext)

    if ext == ".pdf":
        pages = _extract_pdf(file_path)
    elif ext == ".txt":
        pages = _extract_txt(file_path)
    elif ext == ".docx":
        pages = _extract_docx(file_path)
    elif ext in (".csv", ".xlsx", ".xls"):
        pages = _extract_tabular(file_path, ext)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    logger.debug("Extracted %d page(s) from '%s'", len(pages), filename)

    chunks = []
    chunk_idx = 0
    for page_number, text in pages:
        for chunk_text in _split_text(text):
            chunks.append({
                "content": chunk_text.strip(),
                "page_number": page_number,
                "chunk_index": chunk_idx,
                "filename": filename,
            })
            chunk_idx += 1

    final_chunks = [c for c in chunks if c["content"]]
    logger.info("Chunking complete: %d chunks from '%s'", len(final_chunks), filename)
    return final_chunks


def get_page_count(file_path: str, filename: str) -> int:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        with fitz.open(file_path) as doc:
            return len(doc)
    return 1  # single-page concept for non-PDFs


# ---------------------------------------------------------------------------
# Extractors (return list of (page_number, text) tuples)
# ---------------------------------------------------------------------------

def _extract_pdf(file_path: str) -> List[tuple]:
    pages = []
    with fitz.open(file_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                pages.append((i, text))
    return pages


def _extract_txt(file_path: str) -> List[tuple]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return [(None, f.read())]


def _extract_docx(file_path: str) -> List[tuple]:
    doc = DocxDocument(file_path)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    return [(None, full_text)]


def _extract_tabular(file_path: str, ext: str) -> List[tuple]:
    """Convert tabular data to a human-readable text format."""
    if ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # Convert each row to a readable string: "Col1: val | Col2: val | ..."
    rows = []
    for _, row in df.iterrows():
        row_text = " | ".join(f"{col}: {val}" for col, val in row.items())
        rows.append(row_text)

    # Group rows into pages of 50 rows each
    page_size = 50
    pages = []
    for i in range(0, len(rows), page_size):
        page_text = "\n".join(rows[i : i + page_size])
        pages.append((i // page_size + 1, page_text))

    return pages


# ---------------------------------------------------------------------------
# Text Splitter
# ---------------------------------------------------------------------------

def _split_text(text: str) -> List[str]:
    """
    Splits text into overlapping chunks of approximately CHUNK_SIZE characters.
    Tries to break on sentence boundaries ('. ', '? ', '! ', '\n\n').
    """
    # Normalise whitespace a little
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE

        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to find a good sentence boundary near the end
        boundary = _find_boundary(text, end)
        chunks.append(text[start:boundary])

        # Move start forward, keeping an overlap
        start = max(start + 1, boundary - CHUNK_OVERLAP)

    return chunks


def _find_boundary(text: str, pos: int) -> int:
    """Find the nearest sentence-ending boundary around `pos`."""
    window = 100
    search_in = text[max(0, pos - window) : min(len(text), pos + window)]
    offset = max(0, pos - window)

    for sep in [". ", "? ", "! ", "\n\n", "\n"]:
        idx = search_in.rfind(sep, 0, pos - offset + window)
        if idx != -1:
            return offset + idx + len(sep)

    return pos  # fallback: hard cut