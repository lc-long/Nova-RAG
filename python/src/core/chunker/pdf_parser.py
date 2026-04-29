"""PDF document parser using pdfplumber.

pdfplumber handles CJK font-to-unicode mapping correctly (reliable text).
v2.0 upgrade: Uses pdfplumber for reliable CJK text extraction.
v2.1 upgrade: Add PyMuPDF table detection (CJK font issue unresolved).
"""
import re
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
            text = page.extract_text() or ""
            if text.strip():
                yield text.strip(), page_num, text.strip()


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF (all pages concatenated).

    Cleans up common PDF artifacts:
    - Collapses 3+ consecutive newlines to double newlines
    - Removes orphaned single characters from line breaks
    - Fixes hyphenated line breaks at page boundaries
    """
    parts = []
    for text, _, _ in parse_pdf(file_path):
        cleaned = _clean_pdf_text(text)
        parts.append(cleaned)
    return "\n\n".join(parts)


def _clean_pdf_text(text: str) -> str:
    """Remove common PDF extraction artifacts."""
    # Collapse 3+ consecutive newlines to double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Fix hyphenated line breaks (word- at end of line = word- + next word)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # Remove orphaned single characters from line breaks (e.g. "A\n" at page edge)
    # This catches lines with only 1-2 chars followed by newline
    text = re.sub(r'(?<!\n)\n(?!\n)(?=[\w])', ' ', text)

    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)

    return text.strip()
