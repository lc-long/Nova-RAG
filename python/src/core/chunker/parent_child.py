"""Parent-child chunking strategy for RAG.

切分逻辑：
1. Parent chunk: 使用 RecursiveCharacterTextSplitter 按固定长度切分，保留完整语义上下文
2. Child chunk: 从 parent 中进一步切分细小片段，提高检索命中率
3. 存储时建立 parent_id 关联，检索时先找 child 再找 parent
"""
from dataclasses import dataclass
from typing import Optional, list
from langchain.text_splitter import RecursiveCharacterTextSplitter


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
    """Parent-child chunking with configurable sizes using RecursiveCharacterTextSplitter."""

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.overlap = overlap

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""]
        )

    def chunk(self, text: str, doc_id: str) -> list[Chunk]:
        """Split text into parent-child chunks."""
        chunks = []

        parent_chunks = self._create_parent_chunks(text, doc_id)

        for parent in parent_chunks:
            children = self._create_child_chunks(parent, doc_id)
            chunks.append(parent)
            chunks.extend(children)

        return chunks

    def _create_parent_chunks(self, text: str, doc_id: str) -> list[Chunk]:
        """Create parent chunks using RecursiveCharacterTextSplitter."""
        texts = self.text_splitter.split_text(text)
        chunks = []

        for i, content in enumerate(texts):
            if content.strip():
                parent_id = f"{doc_id}_parent_{i}"
                chunks.append(Chunk(
                    chunk_id=parent_id,
                    content=content,
                    doc_id=doc_id,
                    chunk_type="parent",
                    parent_id=None,
                    order=i
                ))

        return chunks

    def _create_child_chunks(self, parent: Chunk, doc_id: str) -> list[Chunk]:
        """Create child chunks from a parent chunk."""
        chunks = []
        text = parent.content
        start = 0
        child_index = 0

        while start < len(text):
            end = min(start + self.child_chunk_size, len(text))

            if end < len(text) and end - start == self.child_chunk_size:
                while end > start and text[end - 1] not in " \t\n":
                    end -= 1
                if end == start:
                    end = min(start + self.child_chunk_size, len(text))

            child_content = text[start:end].strip()
            if child_content:
                child_id = f"{doc_id}_child_{parent.order}_{child_index}"
                chunks.append(Chunk(
                    chunk_id=child_id,
                    content=child_content,
                    doc_id=doc_id,
                    chunk_type="child",
                    parent_id=parent.chunk_id,
                    order=child_index
                ))
                child_index += 1

            start = end - self.overlap if end < len(text) else len(text)

        return chunks