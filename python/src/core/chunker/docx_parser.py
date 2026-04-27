"""DOCX document parser using python-docx."""
from docx import Document


def extract_text_from_docx(file_path: str) -> str:
    """Extract all text from DOCX file."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
