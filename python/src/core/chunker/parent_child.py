from .base import Chunker


class ParentChildChunker(Chunker):
    """Parent-child chunking strategy for RAG."""

    def __init__(self, child_chunk_size: int = 500, child_overlap: int = 50):
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap

    def chunk(self, text: str, doc_id: str) -> list:
        # Stub implementation
        return []
