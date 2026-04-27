"""Sentence-transformers embedding implementation."""
import os
from typing import Optional
from .base import Embedder

# Configure Hugging Face mirror for Chinese network environment
os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")


class SentenceTransformerEmbedder(Embedder):
    """Embedding using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._load_error = None

    @property
    def model(self):
        """Lazy load the model with error handling."""
        if self._load_error is not None:
            raise self._load_error

        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[Embedding] Downloading model {self.model_name} from {os.environ['HF_ENDPOINT']}...")
                self._model = SentenceTransformer(self.model_name)
                print(f"[Embedding] Model {self.model_name} loaded successfully")
            except Exception as e:
                self._load_error = e
                print(f"[Embedding] Failed to load model {self.model_name}: {e}")
                raise

        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        if not texts:
            return []

        if self._load_error is not None:
            raise self._load_error

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            print(f"[Embedding] Embedding generation failed: {e}")
            raise