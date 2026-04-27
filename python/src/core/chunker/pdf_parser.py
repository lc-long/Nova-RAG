"""PDF document parser using pdfplumber."""
from pathlib import Path
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """Parse PDF and yield (text, page_number, full_text).

    Args:
        file_path: Path to PDF file

    Yields:
        Tuple of (text, page_number, full_text)
    """
    import pdfplumber

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                yield text, page_num, text


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF."""
    full_text = []
    for text, _, _ in parse_pdf(file_path):
        full_text.append(text)
    return "\n\n".join(full_text)
