"""PDF document parser with table detection.

Uses both PyMuPDF and pdfplumber for optimal table extraction.
Falls back to pdfplumber if PyMuPDF fails.
"""
import re
import pdfplumber
import fitz  # PyMuPDF
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """Parse PDF and yield (text, page_number, full_text).

    Uses pdfplumber for both text and table extraction (better CJK support).
    Tables are converted to Markdown format.

    Args:
        file_path: Path to PDF file

    Yields:
        Tuple of (text, page_number, full_text)
    """
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Extract tables first
            tables = page.extract_tables()
            table_texts = []
            
            if tables:
                for table in tables:
                    md_table = _table_to_markdown(table)
                    if md_table:
                        table_texts.append(md_table)
            
            # Extract text
            text = page.extract_text() or ""
            
            if table_texts:
                # Remove table regions from text to avoid duplication
                cleaned_text = _remove_table_regions(text, table_texts)
                # Append formatted tables
                table_text = "\n\n".join(table_texts)
                if cleaned_text.strip():
                    full_text = f"{cleaned_text.strip()}\n\n{table_text}"
                else:
                    full_text = table_text
            else:
                full_text = text.strip()
            
            if full_text.strip():
                yield full_text.strip(), page_num, full_text.strip()


def _table_to_markdown(table: list) -> str:
    """Convert a table (list of lists) to Markdown format."""
    try:
        if not table or len(table) < 2:
            return ""
        
        # Clean cell values
        cleaned_data = []
        for row in table:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    # Clean whitespace but preserve structure
                    cell_text = str(cell).strip().replace("\n", " ")
                    # Remove excessive whitespace
                    cell_text = re.sub(r'\s+', ' ', cell_text)
                    cleaned_row.append(cell_text)
            cleaned_data.append(cleaned_row)
        
        # Filter out empty rows
        cleaned_data = [row for row in cleaned_data if any(cell.strip() for cell in row)]
        
        if len(cleaned_data) < 2:
            return ""
        
        # Build Markdown table
        header = cleaned_data[0]
        rows = cleaned_data[1:]
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
            if len(row) > col_count:
                row = row[:col_count]
            md_lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(md_lines)
    except Exception as e:
        print(f"[PDF Parser] Table conversion failed: {e}")
        return ""


def _remove_table_regions(text: str, table_texts: list[str]) -> str:
    """Remove table content from text to avoid duplication."""
    if not text or not table_texts:
        return text
    
    cleaned = text
    for table_text in table_texts:
        # Get first few cells from table header to find in text
        lines = table_text.split("\n")
        if len(lines) >= 3:
            # Extract header cells (remove | and ---)
            header_line = lines[0].replace("|", "").strip()
            if not header_line:
                continue
            
            # Find approximate position in text
            # Use first few words of header as anchor
            header_words = header_line.split()[:3]
            if len(header_words) >= 2:
                anchor = " ".join(header_words)
                idx = cleaned.find(anchor)
                if idx != -1:
                    # Look for end of table (next paragraph or similar structure)
                    end_idx = len(cleaned)
                    # Try to find where table ends (look for patterns like "图", "表", or double newline)
                    for pattern in ["\n\n", "图", "表", "注：", "注:"]:
                        next_occurrence = cleaned.find(pattern, idx + len(anchor))
                        if next_occurrence != -1 and next_occurrence < end_idx:
                            end_idx = next_occurrence
                    
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
