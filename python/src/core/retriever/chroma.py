from .base import Retriever


class ChromaRetriever(Retriever):
    """ChromaDB retriever with parent-child support."""

    def __init__(self, collection_name: str = "lumina_docs"):
        self.collection_name = collection_name

    def retrieve(self, query: str, top_k: int = 5) -> list:
        # Stub implementation
        return []
