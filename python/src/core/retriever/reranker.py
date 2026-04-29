"""Cross-Encoder reranker for post-RRF refinement of retrieval candidates.

Uses a lightweight cross-encoder model (ms-marco-MiniLM-L-6-v2) to score
(query, document) pairs for deep semantic relevance, then reorders the
RRF candidates accordingly.
"""
import os
from typing import Optional

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")


class Reranker:
    """Cross-Encoder reranker using sentence-transformers."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, max_length=512)
        return self._model

    def rerank(self, query: str, candidates: list[dict], top_k: int = 20) -> list[dict]:
        """Rerank candidates by cross-encoder semantic similarity.

        Args:
            query: The original user query.
            candidates: List of chunk dicts from RRF fusion (must have 'parent_content' or 'child_content').
            top_k: Number of top candidates to return after reranking.

        Returns:
            Candidates re-sorted by cross-encoder score descending.
        """
        if not candidates:
            return []

        # Build (query, document) pairs
        pairs = []
        for r in candidates:
            text = r.get("child_content") or r.get("parent_content", "")
            pairs.append((query, text))

        # Get relevance scores
        scores = self.model.predict(pairs)

        # Attach score to each candidate
        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        reranked = []
        for r, score in scored[:top_k]:
            r_copy = dict(r)
            r_copy["rerank_score"] = float(score)
            reranked.append(r_copy)

        return reranked
