"""Aliyun DashScope embedding implementation using OpenAI-compatible API."""
import os
from typing import Optional
from .base import Embedder


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
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]