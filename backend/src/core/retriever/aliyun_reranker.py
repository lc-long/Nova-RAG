"""Aliyun DashScope async reranker implementation."""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("nova_rag")

from ..config import RERANK_MODEL, RERANK_MIN_SCORE


class AliyunReranker:
    """Async reranker using Aliyun DashScope gte-rerank model."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.model = model or RERANK_MODEL
        self.min_relevance_score = RERANK_MIN_SCORE
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-create shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._client

    async def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        """Rerank candidates by semantic relevance using async DashScope API.

        Filters out low-relevance results below MIN_RELEVANCE_SCORE threshold.
        Falls back to original order on network error.
        """
        if not candidates:
            return []

        documents = []
        for r in candidates:
            text = r.get("child_content") or r.get("parent_content", "")
            documents.append(text)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "input": {
                    "query": query,
                    "documents": documents,
                },
                "parameters": {
                    "return_documents": False,
                },
            }
            resp = await self.client.post(self.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("output", {}).get("results", [])
            reranked = []
            for item in results:
                idx = item["index"]
                score = item["relevance_score"]

                # Filter out low-relevance results
                if score < self.min_relevance_score:
                    continue

                r_copy = dict(candidates[idx])
                r_copy["rerank_score"] = score
                reranked.append(r_copy)

            # Sort by relevance score descending
            reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

            return reranked[:top_k]

        except Exception as e:
            logger.warning(f"[Reranker] DashScope rerank failed, falling back to original order: {e}")
            return candidates[:top_k]

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
