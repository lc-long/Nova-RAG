"""PDF document parser with table detection and image extraction.

Uses both PyMuPDF and pdfplumber for optimal table extraction.
Extracts images from PDF for OCR processing.
"""
import re
import os
import base64
import pdfplumber
import fitz  # PyMuPDF
from typing import Generator
from pathlib import Path


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
                # Append formatted tables to text (skip aggressive table region removal
                # which was deleting too much surrounding text)
                table_text = "\n\n".join(table_texts)
                full_text = text.strip()
                if full_text:
                    full_text = f"{full_text}\n\n{table_text}"
                else:
                    full_text = table_text
            else:
                full_text = text.strip()
            
            if full_text.strip():
                yield full_text.strip(), page_num, full_text.strip()


def extract_images_from_pdf(file_path: str, output_dir: str = None) -> list[dict]:
    """Extract images from PDF for OCR processing.

    Args:
        file_path: Path to PDF file
        output_dir: Directory to save extracted images (optional)

    Returns:
        List of dicts with image info: {page_num, image_path, image_base64, bbox}
    """
    images = []
    
    try:
        doc = fitz.open(file_path)
        
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        for page_num, page in enumerate(doc, start=1):
            image_list = page.get_images(full=True)
            
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                
                try:
                    # Extract image
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue
                    
                    image_bytes = base_image["image"]
                    image_ext = base_image.get("ext", "png")
                    
                    # Skip very small images (likely icons or decorations)
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    if width < 50 or height < 50:
                        continue
                    
                    # Convert to base64
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    
                    # Save to file if output_dir specified
                    image_path = None
                    if output_dir:
                        image_name = f"page{page_num}_img{img_idx}.{image_ext}"
                        image_path = os.path.join(output_dir, image_name)
                        with open(image_path, "wb") as f:
                            f.write(image_bytes)
                    
                    # Get image position on page (approximate)
                    bbox = None
                    try:
                        # Try to get image rect from page
                        for block in page.get_text("dict")["blocks"]:
                            if block.get("type") == 1:  # Image block
                                bbox = block.get("bbox")
                                break
                    except Exception:
                        pass
                    
                    images.append({
                        "page_num": page_num,
                        "image_idx": img_idx,
                        "image_path": image_path,
                        "image_base64": image_base64,
                        "image_ext": image_ext,
                        "width": width,
                        "height": height,
                        "bbox": bbox,
                    })
                    
                except Exception as e:
                    print(f"[PDF Parser] Failed to extract image {img_idx} from page {page_num}: {e}")
                    continue
        
        doc.close()
        
    except Exception as e:
        print(f"[PDF Parser] Image extraction failed: {e}")
    
    return images


def get_page_screenshots(file_path: str, output_dir: str = None) -> list[dict]:
    """Convert PDF pages to images (screenshots) for full-page OCR.

    Useful when text extraction fails or for image-heavy pages.

    Args:
        file_path: Path to PDF file
        output_dir: Directory to save screenshots

    Returns:
        List of dicts with page image info
    """
    screenshots = []
    
    try:
        doc = fitz.open(file_path)
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        for page_num, page in enumerate(doc, start=1):
            # Render page to image (2x resolution for better OCR)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to bytes
            image_bytes = pix.tobytes("png")
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Save if output_dir specified
            image_path = None
            if output_dir:
                image_name = f"page{page_num}.png"
                image_path = os.path.join(output_dir, image_name)
                pix.save(image_path)
            
            screenshots.append({
                "page_num": page_num,
                "image_path": image_path,
                "image_base64": image_base64,
                "width": pix.width,
                "height": pix.height,
            })
        
        doc.close()
        
    except Exception as e:
        print(f"[PDF Parser] Page screenshot failed: {e}")
    
    return screenshots


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


# Sentinel used to mark page boundaries (stripped before chunking)
_PAGE_MARKER = "\x00PAGE_SEP\x00"


def extract_text_from_pdf_with_pages(file_path: str) -> tuple[str, list[int]]:
    """Extract PDF text with page boundary markers for OCR insertion.

    Returns:
        (text_with_markers, page_offsets) where page_offsets[i] = char offset
        of the start of page (i+1) in the text.
    """
    pages = []
    for text, page_num, _ in parse_pdf(file_path):
        cleaned = _clean_pdf_text(text)
        pages.append((page_num, cleaned))
    return pages


def merge_ocr_into_text(pages: list[tuple[int, str]], ocr_results: list[dict]) -> str:
    """Merge OCR image descriptions into their corresponding page text.

    Args:
        pages: List of (page_number, page_text) from extract_text_from_pdf_with_pages
        ocr_results: List of dicts with page_num, description from OCR

    Returns:
        Full text with OCR descriptions inserted at the correct page positions
    """
    # Build a dict of page_num -> list of descriptions
    ocr_by_page: dict[int, list[str]] = {}
    for img in ocr_results:
        page_num = img.get("page_num", 0)
        desc = img.get("description", "")
        if desc:
            ocr_by_page.setdefault(page_num, []).append(desc)

    # Merge
    parts = []
    for page_num, page_text in pages:
        if page_text.strip():
            parts.append(page_text)
        # Insert any OCR descriptions for this page
        if page_num in ocr_by_page:
            for desc in ocr_by_page[page_num]:
                parts.append(f"[Page {page_num} Image]: {desc}")

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
