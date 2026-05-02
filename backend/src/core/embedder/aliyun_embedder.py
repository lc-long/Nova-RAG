"""Aliyun DashScope embedding implementation using OpenAI-compatible API."""
import os
import time
from typing import Optional
from .base import Embedder
from ..config import EMBED_MODEL, EMBED_BASE_URL, EMBED_BATCH_SIZE, EMBED_BATCH_SLEEP, EMBED_MAX_TEXT_CHARS


class AliyunEmbedder(Embedder):
    """Embedding using Aliyun DashScope text-embedding-v3."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.model = model or EMBED_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=EMBED_BASE_URL,
            )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Truncate oversized texts to protect against API limits
        safe_texts: list[str] = []
        for t in texts:
            if len(t) > EMBED_MAX_TEXT_CHARS:
                print(f"[Embedder] Warning: text chunk truncated from {len(t)} to {EMBED_MAX_TEXT_CHARS} characters to fit API limits.")
                t = t[:EMBED_MAX_TEXT_CHARS]
            safe_texts.append(t)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(safe_texts), EMBED_BATCH_SIZE):
            if i > 0:
                time.sleep(EMBED_BATCH_SLEEP)
            batch = safe_texts[i:i + EMBED_BATCH_SIZE]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            all_embeddings.extend(item.embedding for item in response.data)
        return all_embeddings