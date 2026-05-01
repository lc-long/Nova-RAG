"""PDF document parser with table detection.

Uses PyMuPDF for table detection and pdfplumber for reliable CJK text extraction.
Tables are extracted separately and formatted as Markdown for better readability.
"""
import re
import pdfplumber
import fitz  # PyMuPDF
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """Parse PDF and yield (text, page_number, full_text).

    Uses PyMuPDF for table detection and pdfplumber for text extraction.
    Tables are converted to Markdown format for better chunking.

    Args:
        file_path: Path to PDF file

    Yields:
        Tuple of (text, page_number, full_text)
    """
    # First pass: detect tables with PyMuPDF
    tables_by_page = _extract_tables_with_pymupdf(file_path)

    # Second pass: extract text with pdfplumber (better CJK support)
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Get regular text
            text = page.extract_text() or ""

            # Get tables for this page
            page_tables = tables_by_page.get(page_num, [])

            # Combine text and tables
            if page_tables:
                # Remove table regions from text to avoid duplication
                cleaned_text = _remove_table_regions(text, page_tables)
                # Append formatted tables
                table_text = "\n\n".join(page_tables)
                if cleaned_text.strip():
                    full_text = f"{cleaned_text.strip()}\n\n{table_text}"
                else:
                    full_text = table_text
            else:
                full_text = text.strip()

            if full_text.strip():
                yield full_text.strip(), page_num, full_text.strip()


def _extract_tables_with_pymupdf(file_path: str) -> dict[int, list[str]]:
    """Extract tables from PDF using PyMuPDF and format as Markdown.

    Returns:
        Dict mapping page_number to list of Markdown-formatted table strings
    """
    tables_by_page = {}

    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc, start=1):
            tables = page.find_tables()
            if not tables or not tables.tables:
                continue

            page_tables = []
            for table in tables.tables:
                md_table = _table_to_markdown(table)
                if md_table:
                    page_tables.append(md_table)

            if page_tables:
                tables_by_page[page_num] = page_tables

        doc.close()
    except Exception as e:
        print(f"[PDF Parser] PyMuPDF table extraction failed: {e}")

    return tables_by_page


def _table_to_markdown(table) -> str:
    """Convert a PyMuPDF table to Markdown format."""
    try:
        data = table.extract()
        if not data or len(data) < 2:
            return ""

        # Clean cell values
        cleaned_data = []
        for row in data:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    # Clean whitespace but preserve structure
                    cleaned_row.append(str(cell).strip().replace("\n", " "))
            cleaned_data.append(cleaned_row)

        # Build Markdown table
        header = cleaned_data[0]
        rows = cleaned_data[1:]

        # Calculate column widths
        col_count = len(header)
        md_lines = []

        # Header row
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("| " + " | ".join(["---"] * col_count) + " |")

        # Data rows
        for row in rows:
            # Ensure row has same number of columns
            while len(row) < col_count:
                row.append("")
            md_lines.append("| " + " | ".join(row[:col_count]) + " |")

        return "\n".join(md_lines)
    except Exception as e:
        print(f"[PDF Parser] Table conversion failed: {e}")
        return ""


def _remove_table_regions(text: str, table_texts: list[str]) -> str:
    """Remove table content from text to avoid duplication.

    This is a best-effort approach since exact matching is difficult.
    """
    if not text or not table_texts:
        return text

    cleaned = text
    for table_text in table_texts:
        # Try to find and remove table header (first row) from text
        lines = table_text.split("\n")
        if len(lines) >= 3:  # At least header + separator + one row
            # Use first data row as anchor (more unique than header)
            header_line = lines[0].replace("|", "").strip()
            # Find approximate position in text
            if header_line in cleaned:
                # Find the start of this region
                idx = cleaned.find(header_line)
                # Look for end of table (next paragraph or end of text)
                end_idx = len(cleaned)
                # Simple heuristic: table ends at double newline
                next_para = cleaned.find("\n\n", idx)
                if next_para != -1:
                    end_idx = next_para
                cleaned = cleaned[:idx] + cleaned[end_idx:]

    return cleaned


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF (all pages concatenated).

    Tables are formatted as Markdown for better readability.
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

    # Remove orphaned single characters from line breaks
    text = re.sub(r'(?<!\n)\n(?!\n)(?=[\w])', ' ', text)

    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)

    return text.strip()
