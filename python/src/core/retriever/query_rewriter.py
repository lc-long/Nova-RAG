"""LLM-based query rewriter to expand queries with synonyms and format variations.

Addresses the vocabulary mismatch problem where user phrasing (e.g., "限制高度 30m")
doesn't match document phrasing (e.g., "限高 30 m").
"""
import os
from typing import Optional

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")


class QueryRewriter:
    """Expands a user query into multiple rewrite variants using LLM."""

    SYSTEM_PROMPT = (
        "你是一个专业的检索词优化专家。用户输入了一个查询，请提取核心关键词，"
        "并补充同义词、缩写、不同空格格式（如 30m -> 30 m，限制高度 -> 限高）。"
        "输出 3-5 个用逗号分隔的搜索短语，不要输出多余解释。"
    )

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._client = None

    @property
    def client(self):
        """Lazy-load Minimax client only when needed."""
        if self._client is None:
            from ..llm.minimax import MinimaxClient
            self._client = MinimaxClient()
        return self._client

    def rewrite(self, user_query: str) -> list[str]:
        """Rewrite a single user query into multiple search variants.

        Args:
            user_query: Original user query string.

        Returns:
            List of query strings including the original and rewrites.
        """
        if not user_query or not user_query.strip():
            return [user_query]

        prompt = f"{self.SYSTEM_PROMPT}\n\n用户查询：{user_query}"

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "MiniMax-M2.7",
                "group_id": self.client.group_id,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            response = requests.post(
                f"{self.client.base_url}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
                timeout=15
            )

            if response.status_code != 200:
                return [user_query]

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return [user_query]

            content = choices[0].get("message", {}).get("content", "")
            rewrites = self._parse_rewrites(content)
            return rewrites if rewrites else [user_query]

        except Exception:
            return [user_query]

    def _parse_rewrites(self, content: str) -> list[str]:
        """Parse LLM response into a list of query strings."""
        if not content:
            return []

        rewrites = [s.strip() for s in content.split(",")]
        rewrites = [s for s in rewrites if s and len(s) > 1]
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for r in rewrites:
            norm = r.replace(" ", "").lower()
            if norm not in seen:
                seen.add(norm)
                unique.append(r)
        return unique

    def rewrite_with_fallback(self, user_query: str) -> list[str]:
        """Rewrite with built-in fallback patterns when LLM is unavailable.

        Provides common aviation/DRONE specific expansions as a safety net.
        """
        rewrites = self.rewrite(user_query)
        if len(rewrites) <= 1:
            # LLM failed or returned nothing, use pattern-based expansion
            rewrites = self._pattern_expand(user_query)
        return rewrites

    def _pattern_expand(self, query: str) -> list[str]:
        """Fallback pattern-based expansion for drone/aviation queries."""
        expansions = [query]

        # Common drone vocabulary variations
        replacements = [
            ("限制高度", ["限高", "限制高", "限高30m", "限高 30m", "限高30 m"]),
            ("限制距离", ["限远", "限制远", "限远50m", "限远 50m", "限远50 m"]),
            ("30m", ["30 m", "30m", "30米"]),
            ("50m", ["50 m", "50m", "50米"]),
        ]

        for original, variants in replacements:
            if original in query:
                for v in variants:
                    expanded = query.replace(original, v)
                    if expanded not in expansions:
                        expansions.append(expanded)

        return expansions[:5]


def rewrite_query(user_query: str) -> list[str]:
    """Convenience function for query rewriting.

    Returns the original query plus 3-5 LLM-generated rewrites.
    Falls back to pattern-based expansion if LLM is unavailable.
    """
    rewriter = QueryRewriter()
    return rewriter.rewrite_with_fallback(user_query)
