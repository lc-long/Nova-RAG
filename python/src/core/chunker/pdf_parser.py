"""PDF document parser using PyMuPDF (fitz).

Upgraded from pdfplumber to PyMuPDF for better table detection and
improved handling of complex PDF layouts.
"""
import re
import fitz  # PyMuPDF
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """Parse PDF and yield (text_with_tables, page_number, full_text).

    Strategy:
    1. Extract all text blocks (preserving reading order via block positions)
    2. Detect tables using page.find_tables() and convert them to Markdown
    3. Interleave table Markdown with surrounding text in natural reading order
    4. Fall back to plain text extraction if no tables detected

    Args:
        file_path: Path to PDF file

    Yields:
        Tuple of (text_with_tables, page_number, full_text)
    """
    doc = fitz.open(file_path)

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")  # natural reading order
        if not page_text.strip():
            continue

        # Detect tables on this page
        tables = page.find_tables()
        table_list = tables.tables if tables else []

        if not table_list:
            # No tables: yield plain text
            yield page_text.strip(), page_num, page_text.strip()
            continue

        # Build a list of (y_boundary, content) to merge tables into text
        # Tables have bbox (x0, y0, x1, y1)
        markers = []  # list of (y_position, 'table_start'|'table_end'|'text', content)

        # Get text blocks sorted by vertical position
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: b[0])  # sort by y0 (top to bottom)

        # Collect all table bounding boxes
        table_bboxes = [(t.bbox[1], t.bbox[3]) for t in table_list]  # (top, bottom)

        text_parts = []
        current_y = 0

        # Walk through blocks and tables in vertical order
        for block in blocks:
            block_y0 = block[1]
            block_y1 = block[3]
            block_text = block[4].strip()

            if not block_text:
                continue

            # Check if any table starts within this block's y range
            for table_top, table_bottom in table_bboxes:
                if block_y0 <= table_top < block_y1 and block_y0 < table_bottom:
                    # This block overlaps with or precedes a table
                    # First yield the block text before the table
                    pass

        # Simpler approach: process tables and text sequentially by y-position
        content_items = []  # (start_y, type, content)

        # Add text blocks
        for block in blocks:
            block_text = block[4].strip()
            if not block_text:
                continue
            content_items.append((block[1], "text", block_text))

        # Add tables
        for t in table_list:
            md_table = _table_to_markdown(t)
            if md_table:
                content_items.append((t.bbox[1], "table", md_table))

        # Sort by y position and merge
        content_items.sort(key=lambda x: x[0])

        page_parts = []
        for _, kind, content in content_items:
            if kind == "text":
                page_parts.append(content)
            elif kind == "table":
                page_parts.append(content)

        combined = "\n\n".join(page_parts)
        if combined.strip():
            yield combined.strip(), page_num, combined.strip()

    doc.close()


def _table_to_markdown(table) -> str:
    """Convert a PyMuPDF table to a Markdown table string.

    Handles both older dict format (extracted["data"]) and
    newer list format (extracted as list of rows).
    """
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

    # Determine column count from longest row
    col_count = max(len(row) for row in rows) if rows else 0
    if col_count == 0:
        return ""

    # Build header row — use first row if it looks like a header
    header_row = list(rows[0]) if rows else []
    if not all(cell and str(cell).strip() for cell in header_row):
        # First row is not a proper header — generate generic column names
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
        # Pad or trim to col_count
        if len(cells) < col_count:
            cells.extend([""] * (col_count - len(cells)))
        elif len(cells) > col_count:
            cells = cells[:col_count]
        md_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(md_lines)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF (all pages concatenated)."""
    parts = []
    for text, _, _ in parse_pdf(file_path):
        parts.append(text)
    return "\n\n".join(parts)
