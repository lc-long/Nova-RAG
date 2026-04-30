from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    content: str
    doc_id: str
    parent_id: Optional[str] = None
    page_number: Optional[int] = None


@dataclass
class ParentDoc:
    doc_id: str
    content: str
    name: str
