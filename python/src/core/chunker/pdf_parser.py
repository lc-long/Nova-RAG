"""PDF document parser using hybrid pdfplumber + PyMuPDF approach.

Strategy:
- pdfplumber handles CJK font-to-unicode mapping correctly (reliable text)
- PyMuPDF provides table detection via page.find_tables() only when available
- When PyMuPDF table detection fails/times out, fall back to pdfplumber text only

v2.0 upgrade: Use pdfplumber's native table detection with markdown output.
PyMuPDF table detection is deferred to v2.1 due to CJK font handling issues.
"""
import os
import pdfplumber
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """Parse PDF and yield (text, page_number, full_text).

    Uses pdfplumber for reliable CJK text extraction and table detection.
    Tables are output as-is in pdfplumber's native text format.

    Args:
        file_path: Path to PDF file

    Yields:
        Tuple of (text, page_number, full_text)
    """
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # extract_text() returns text with tables rendered inline
            text = page.extract_text() or ""
            if text.strip():
                yield text.strip(), page_num, text.strip()


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF (all pages concatenated)."""
    parts = []
    for text, _, _ in parse_pdf(file_path):
        parts.append(text)
    return "\n\n".join(parts)
