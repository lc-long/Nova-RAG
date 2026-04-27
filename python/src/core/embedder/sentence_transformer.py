from .base import Embedder


class SentenceTransformerEmbedder(Embedder):
    """Embedding using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Stub implementation
        return []
