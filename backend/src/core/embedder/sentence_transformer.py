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
    _model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    _load_error: Optional[Exception] = None

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        pass

    @classmethod
    def get_instance(cls, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> "SentenceTransformerEmbedder":
        """Get singleton instance, loading model only once."""
        if cls._instance is None:
            if model_name and model_name != "paraphrase-multilingual-MiniLM-L12-v2":
                cls._model_name = model_name
            cls._instance = cls()
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
                print(f"[Embedding] Loading model {cls._model_name} (local_files_only)...")
                cls._model = SentenceTransformer(cls._model_name, device="cpu")
                print(f"[Embedding] Model {cls._model_name} loaded successfully")
            except Exception as e:
                cls._load_error = e
                print(f"[Embedding] Failed to load model {cls._model_name}: {e}")
                raise

    @property
    def model(self):
        """Get model, raising any load error."""
        if type(self)._load_error is not None:
            raise type(self)._load_error
        if type(self)._model is None:
            type(self)._ensure_model_loaded()
        return type(self)._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        if not texts:
            return []

        if type(self)._load_error is not None:
            raise type(self)._load_error

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            print(f"[Embedding] Embedding generation failed: {e}")
            raise