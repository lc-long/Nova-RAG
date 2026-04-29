"""DOCX document parser with UTF-8 preservation and table-to-Markdown conversion."""
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _extract_para_text(p_elem) -> str:
    """Extract plain text from a <w:p> element, preserving runs inline."""
    texts = []
    for r in p_elem.iter(f"{{{W_NS}}}t"):
        if r.text:
            texts.append(r.text)
    return "".join(texts)


def _cell_text(cell_elem) -> str:
    """Extract text from a <w:tc> cell element, joining paragraphs with spaces."""
    parts = []
    for p in cell_elem.iter(f"{{{W_NS}}}p"):
        cell_para_text = _extract_para_text(p)
        if cell_para_text.strip():
            parts.append(cell_para_text)
    return " ".join(parts)


def _tbl_to_markdown(tbl_elem) -> str:
    """Convert a <w:tbl> element to a Markdown table string."""
    rows = list(tbl_elem.iter(f"{{{W_NS}}}tr"))
    if not rows:
        return ""

    markdown_rows = []
    for row_idx, tr in enumerate(rows):
        cells = list(tr.iter(f"{{{W_NS}}}tc"))
        cell_texts = [_cell_text(c).strip() for c in cells]
        markdown_rows.append("| " + " | ".join(cell_texts) + " |")
        # Add separator after first (header) row
        if row_idx == 0:
            col_count = len(cells)
            markdown_rows.append("| " + " | ".join(["---"] * col_count) + " |")

    return "\n".join(markdown_rows)


def extract_text_from_docx(file_path: str) -> str:
    """Extract all text from DOCX, preserving paragraph order and converting tables to Markdown."""
    doc = Document(file_path)
    body = doc.element.body
    blocks = []

    for child in body.iterchildren():
        if isinstance(child, CT_P):
            text = _extract_para_text(child)
            if text.strip():
                blocks.append(text)
        elif isinstance(child, CT_Tbl):
            md_table = _tbl_to_markdown(child)
            if md_table.strip():
                blocks.append(md_table)

    return "\n\n".join(blocks)
