"""Sentence-transformers embedding implementation."""
import os
from typing import Optional, Any
from .base import Embedder

# Configure Hugging Face mirror for Chinese network environment
os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")


class SentenceTransformerEmbedder(Embedder):
    """Embedding using sentence-transformers with singleton model."""

    _instance: Optional["SentenceTransformerEmbedder"] = None
    _model: Optional[Any] = None
    _load_error: Optional[Exception] = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    @classmethod
    def get_instance(cls, model_name: str = "all-MiniLM-L6-v2") -> "SentenceTransformerEmbedder":
        """Get singleton instance, loading model only once."""
        if cls._instance is None:
            cls._instance = cls(model_name)
            cls._ensure_model_loaded()
        return cls._instance

    @classmethod
    def _ensure_model_loaded(cls) -> None:
        """Load model at singleton initialization."""
        if cls._load_error is not None:
            raise cls._load_error

        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[Embedding] Downloading model {cls._instance.model_name} from {os.environ.get('HF_ENDPOINT', 'huggingface.co')}...")
                cls._model = SentenceTransformer(cls._instance.model_name)
                print(f"[Embedding] Model {cls._instance.model_name} loaded successfully")
            except Exception as e:
                cls._load_error = e
                print(f"[Embedding] Failed to load model {cls._instance.model_name}: {e}")
                raise

    @property
    def model(self):
        """Get model, raising any load error."""
        if self._load_error is not None:
            raise self._load_error
        if self._model is None:
            self._ensure_model_loaded()
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