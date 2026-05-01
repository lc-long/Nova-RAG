"""Aliyun DashScope reranker implementation."""
import os
from typing import Optional
import httpx


class AliyunReranker:
    """Reranker using Aliyun DashScope gte-rerank model."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gte-rerank"):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.model = model
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-reranking/text-reranking"

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        """Rerank candidates by semantic relevance using DashScope API.

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
            resp = httpx.post(self.api_url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("output", {}).get("results", [])
            reranked = []
            for item in results:
                idx = item["index"]
                score = item["relevance_score"]
                r_copy = dict(candidates[idx])
                r_copy["rerank_score"] = score
                reranked.append(r_copy)

            return reranked[:top_k]

        except Exception as e:
            print(f"[Reranker] DashScope rerank failed, falling back to original order: {e}")
            return candidates[:top_k]
