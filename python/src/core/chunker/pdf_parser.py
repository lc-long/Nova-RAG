"""PDF document parser using hybrid pdfplumber + PyMuPDF approach.

Strategy:
- pdfplumber handles CJK font-to-unicode mapping correctly (reliable text)
- PyMuPDF (fitz) provides superior table detection via page.find_tables()
- Tables are detected by PyMuPDF, then replaced with markdown equivalents
  in the pdfplumber text using bbox position matching

This gives us reliable international text AND better table detection,
addressing the weaknesses of each library individually.
"""
import fitz  # PyMuPDF
import pdfplumber
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """Parse PDF and yield (text_with_tables, page_number, full_text).

    Hybrid approach:
    1. Extract base text via pdfplumber (reliable CJK)
    2. Detect tables via PyMuPDF find_tables()
    3. Convert PyMuPDF tables to markdown
    4. Replace table regions in pdfplumber text with markdown tables

    Args:
        file_path: Path to PDF file

    Yields:
        Tuple of (text_with_tables, page_number, full_text)
    """
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            pdf_text = page.extract_text() or ""
            if not pdf_text.strip():
                continue

            # Use PyMuPDF for table detection on this page
            doc = fitz.open(file_path)
            mupdf_page = doc[page_num - 1]

            tables = mupdf_page.find_tables()
            table_list = tables.tables if tables else []
            doc.close()

            if not table_list:
                yield pdf_text.strip(), page_num, pdf_text.strip()
                continue

            # Convert tables to markdown and track their bboxes
            md_tables = []
            for t in table_list:
                md = _table_to_markdown(t)
                if md:
                    md_tables.append((t.bbox, md))

            if not md_tables:
                yield pdf_text.strip(), page_num, pdf_text.strip()
                continue

            # Replace table regions with markdown equivalents
            text_with_tables = _inject_markdown_tables(pdf_text, md_tables)
            yield text_with_tables.strip(), page_num, pdf_text.strip()


def _table_to_markdown(table) -> str:
    """Convert a PyMuPDF table to a Markdown table string."""
    try:
        extracted = table.extract()
    except Exception:
        return ""

    if not extracted:
        return ""

    # Normalize to list of lists (rows)
    if isinstance(extracted, dict):
        rows = extracted.get("data", [])
    elif isinstance(extracted, list):
        rows = extracted
    else:
        return ""

    if not rows or not isinstance(rows, list):
        return ""

    col_count = max(len(row) for row in rows) if rows else 0
    if col_count == 0:
        return ""

    header_row = list(rows[0]) if rows else []
    if not all(cell and str(cell).strip() for cell in header_row):
        header = [f"Col{i+1}" for i in range(col_count)]
        data_rows = rows
    else:
        header = [str(cell).strip() if cell else "" for cell in header_row]
        data_rows = rows[1:]

    md_lines = []
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * col_count) + " |")

    for row in data_rows:
        cells = [str(cell).strip() if cell else "" for cell in row]
        if len(cells) < col_count:
            cells.extend([""] * (col_count - len(cells)))
        elif len(cells) > col_count:
            cells = cells[:col_count]
        md_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(md_lines)


def _inject_markdown_tables(pdf_text: str, md_tables: list) -> str:
    """Replace table regions in pdfplumber text with markdown equivalents.

    Since pdfplumber and PyMuPDF use different coordinate systems, we
    can't directly map bboxes. Instead, we detect likely table regions
    in the pdfplumber text (lines with many | characters) and replace
    them with the corresponding markdown table.
    """
    lines = pdf_text.split("\n")
    result = []
    table_idx = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line looks like part of a pdfplumber table
        # pdfplumber renders tables with pipe characters and spacing
        if "|" in line and line.strip().startswith("|"):
            # Collect consecutive table lines
            table_lines = [line]
            j = i + 1
            while j < len(lines) and "|" in lines[j] and lines[j].strip().startswith("|"):
                table_lines.append(lines[j])
                j += 1

            # Replace with markdown table from PyMuPDF if available
            if table_idx < len(md_tables):
                _, md_table = md_tables[table_idx]
                result.append(md_table)
                table_idx += 1
            else:
                # No more markdown tables, keep original
                result.extend(table_lines)
            i = j
        else:
            result.append(line)
            i += 1

    return "\n".join(result)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF (all pages concatenated)."""
    parts = []
    for text, _, _ in parse_pdf(file_path):
        parts.append(text)
    return "\n\n".join(parts)