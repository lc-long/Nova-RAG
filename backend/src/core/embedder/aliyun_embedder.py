"""Aliyun DashScope embedding implementation using OpenAI-compatible API."""
import os
import time
from typing import Optional
from .base import Embedder

_BATCH_SIZE = 6       # DashScope limit is 10; use 6 for safety margin
_BATCH_SLEEP = 0.1    # seconds between batches to avoid QPS throttling
_MAX_TEXT_CHARS = 6000  # DashScope limit is 8192 tokens; ~6000 chars is safe


class AliyunEmbedder(Embedder):
    """Embedding using Aliyun DashScope text-embedding-v3."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-v3"):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Truncate oversized texts to protect against API limits
        safe_texts: list[str] = []
        for t in texts:
            if len(t) > _MAX_TEXT_CHARS:
                print(f"[Embedder] Warning: text chunk truncated from {len(t)} to {_MAX_TEXT_CHARS} characters to fit API limits.")
                t = t[:_MAX_TEXT_CHARS]
            safe_texts.append(t)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(safe_texts), _BATCH_SIZE):
            if i > 0:
                time.sleep(_BATCH_SLEEP)
            batch = safe_texts[i:i + _BATCH_SIZE]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            all_embeddings.extend(item.embedding for item in response.data)
        return all_embeddings