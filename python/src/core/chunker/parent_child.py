"""Parent-child chunking strategy for RAG.

切分逻辑：
1. Parent chunk: 按段落/固定长度切分，保留完整语义上下文
2. Child chunk: 从 parent 中进一步切分细小片段，提高检索命中率
3. 存储时建立 parent_id 关联，检索时先找 child 再找 parent
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    content: str
    doc_id: str
    chunk_type: str  # "parent" or "child"
    parent_id: Optional[str] = None
    page_number: Optional[int] = None
    order: int = 0


class ParentChildChunker:
    """Parent-child chunking with configurable sizes."""

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, doc_id: str) -> list[Chunk]:
        """Split text into parent-child chunks."""
        chunks = []

        # First create parent chunks
        parent_chunks = self._create_parent_chunks(text, doc_id)

        # Then create child chunks from each parent
        for parent in parent_chunks:
            children = self._create_child_chunks(parent, doc_id)
            chunks.append(parent)
            chunks.extend(children)

        return chunks

    def _create_parent_chunks(self, text: str, doc_id: str) -> list[Chunk]:
        """Create parent chunks from text."""
        chunks = []
        paragraphs = text.split("\n\n")
        current_parent = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)
            if current_size + para_size > self.parent_chunk_size and current_parent:
                parent_id = f"{doc_id}_parent_{len(chunks)}"
                content = "\n\n".join(current_parent)
                chunks.append(Chunk(
                    chunk_id=parent_id,
                    content=content,
                    doc_id=doc_id,
                    chunk_type="parent",
                    parent_id=None,
                    order=len(chunks)
                ))
                current_parent = []
                current_size = 0

            current_parent.append(para)
            current_size += para_size

        # Handle remaining content
        if current_parent:
            parent_id = f"{doc_id}_parent_{len(chunks)}"
            content = "\n\n".join(current_parent)
            chunks.append(Chunk(
                chunk_id=parent_id,
                content=content,
                doc_id=doc_id,
                chunk_type="parent",
                parent_id=None,
                order=len(chunks)
            ))

        return chunks

    def _create_child_chunks(self, parent: Chunk, doc_id: str) -> list[Chunk]:
        """Create child chunks from a parent chunk."""
        chunks = []
        text = parent.content
        start = 0

        while start < len(text):
            end = min(start + self.child_chunk_size, len(text))

            if end < len(text) and end - start == self.child_chunk_size:
                while end > start and text[end - 1] not in " \t\n":
                    end -= 1
                if end == start:
                    end = min(start + self.child_chunk_size, len(text))

            child_content = text[start:end].strip()
            if child_content:
                child_id = f"{doc_id}_child_{len(chunks)}"
                chunks.append(Chunk(
                    chunk_id=child_id,
                    content=child_content,
                    doc_id=doc_id,
                    chunk_type="child",
                    parent_id=parent.chunk_id,
                    order=len(chunks)
                ))

            start = end - self.overlap if end < len(text) else len(text)

        return chunks
