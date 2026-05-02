"""LLM-based async query rewriter to expand queries with synonyms and format variations.

Addresses the vocabulary mismatch problem where user phrasing (e.g., "限制高度 30m")
doesn't match document phrasing (e.g., "限高 30 m").
"""
import json
import os
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import httpx

from ..config import SHORT_QUERY_THRESHOLD, QUERY_PATTERNS_FILE

logger = logging.getLogger("nova_rag")

_CACHE_MAX_SIZE = 512


class QueryRewriter:
    """Expands a user query into multiple rewrite variants using async LLM."""

    SYSTEM_PROMPT = (
        "你是一个专业的检索词优化专家。用户输入了一个查询，请：\n"
        "1. 提取核心关键词\n"
        "2. 补充同义词、缩写、不同空格格式\n"
        "3. 如果查询是中文，同时提供英文翻译版本（知识库可能包含中英文混合内容）\n"
        "输出 3-5 个用逗号分隔的搜索短语，中英文都要包含，不要输出多余解释。"
    )

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._client = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._cache: OrderedDict[str, list[str]] = OrderedDict()
        self._patterns = self._load_patterns()

    def _cache_set(self, key: str, value: list[str]):
        """Set cache entry with LRU eviction when size limit is reached."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > _CACHE_MAX_SIZE:
            self._cache.popitem(last=False)

    @property
    def client(self):
        """Lazy-load Minimax client only when needed."""
        if self._client is None:
            from ..llm.minimax import MinimaxClient
            self._client = MinimaxClient()
        return self._client

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-create shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http_client

    def _load_patterns(self) -> list[tuple[str, list[str]]]:
        """Load expansion patterns from config file or use defaults."""
        default = [
            ("限制高度", ["限高", "限制高", "限高30m", "限高 30m", "限高30 m"]),
            ("限制距离", ["限远", "限制远", "限远50m", "限远 50m", "限远50 m"]),
            ("30m", ["30 m", "30m", "30米"]),
            ("50m", ["50 m", "50m", "50米"]),
            ("饼状图", ["pie chart", "饼图", "Pie Chart", "Revenue Distribution"]),
            ("柱状图", ["bar chart", "Bar Chart", "条形图"]),
            ("折线图", ["line chart", "Line Chart", "趋势图"]),
            ("表格", ["table", "Table", "数据表"]),
            ("产品", ["product", "Product", "产品规格"]),
            ("收入", ["revenue", "Revenue", "营收"]),
            ("分布", ["distribution", "Distribution", "占比"]),
            ("架构图", ["architecture", "Architecture", "系统架构", "Technical Architecture", "microservices"]),
            ("流程图", ["flowchart", "Flow Chart", "pipeline", "Pipeline"]),
            ("部署", ["deploy", "Deploy", "deployment", "Deployment"]),
            ("安全", ["security", "Security", "框架", "Framework"]),
            ("性能", ["performance", "Performance", "指标", "Metrics"]),
        ]
        if not QUERY_PATTERNS_FILE:
            return default
        try:
            data = json.loads(Path(QUERY_PATTERNS_FILE).read_text(encoding="utf-8"))
            return [(p["original"], p["variants"]) for p in data.get("patterns", [])] or default
        except Exception:
            return default

    async def rewrite(self, user_query: str) -> list[str]:
        """Rewrite a single user query into multiple search variants.

        Skips LLM for short queries to improve response time.

        Args:
            user_query: Original user query string.

        Returns:
            List of query strings including the original and rewrites.
        """
        if not user_query or not user_query.strip():
            return [user_query]

        # Check cache first
        cache_key = user_query.strip().lower()
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        # Skip LLM for short queries - use pattern expansion only
        if len(user_query) < SHORT_QUERY_THRESHOLD:
            result = self._pattern_expand(user_query)
            self._cache_set(cache_key, result)
            return result

        prompt = f"{self.SYSTEM_PROMPT}\n\n用户查询：{user_query}"

        try:
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

            response = await self.http_client.post(
                f"{self.client.base_url}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                result = [user_query]
                self._cache_set(cache_key, result)
                return result

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                result = [user_query]
                self._cache_set(cache_key, result)
                return result

            content = choices[0].get("message", {}).get("content", "")
            rewrites = self._parse_rewrites(content)
            result = rewrites if rewrites else [user_query]
            self._cache_set(cache_key, result)
            return result

        except Exception:
            result = [user_query]
            self._cache_set(cache_key, result)
            return result

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

    async def rewrite_with_fallback(self, user_query: str) -> list[str]:
        """Rewrite with built-in fallback patterns when LLM is unavailable.

        Provides common aviation/DRONE specific expansions as a safety net.
        """
        rewrites = await self.rewrite(user_query)
        if len(rewrites) <= 1:
            # LLM failed or returned nothing, use pattern-based expansion
            rewrites = self._pattern_expand(user_query)
        return rewrites

    def _pattern_expand(self, query: str) -> list[str]:
        """Fallback pattern-based expansion using configurable rules."""
        expansions = [query]

        for original, variants in self._patterns:
            if original in query:
                for v in variants:
                    expanded = query.replace(original, v)
                    if expanded not in expansions:
                        expansions.append(expanded)

        return expansions[:5]

    async def close(self):
        """Close the underlying HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


async def rewrite_query(user_query: str) -> list[str]:
    """Convenience function for query rewriting.

    Returns the original query plus 3-5 LLM-generated rewrites.
    Falls back to pattern-based expansion if LLM is unavailable.
    """
    rewriter = QueryRewriter()
    return await rewriter.rewrite_with_fallback(user_query)
