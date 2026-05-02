"""LLM-based async query rewriter with semantic cache and PRF fallback.

Query expansion strategies:
1. Semantic cache: if similar query was cached (cosine > 0.95), reuse rewrites
2. LLM expansion: generate variants using prompt template
3. PRF fallback: extract top terms from initial retrieval (last resort)

Addresses vocabulary mismatch where user phrasing differs from document phrasing.
"""
import asyncio
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import httpx

from ..config import SHORT_QUERY_THRESHOLD, QUERY_PATTERNS_FILE

logger = logging.getLogger("nova_rag")

_CACHE_MAX_SIZE = 512
_SEMANTIC_THRESHOLD = 0.95


class QueryRewriter:
    """Expands a user query into multiple rewrite variants using async LLM."""

    SYSTEM_PROMPT = (
        "对于<原始查询>，补充其上位概念、下位具体场景及相关关联词，用|分隔。\n"
        "示例：跑步 → 运动|慢跑|马拉松|跑鞋|运动手环\n"
        "示例：服务器部署 → 云部署|docker|kubernetes|k8s|运维\n"
        "输出格式：用|分隔的搜索词列表，不要输出多余解释。"
    )

    def __init__(self, llm_client=None, embedder=None):
        self.llm_client = llm_client
        self.embedder = embedder
        self._client = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._cache: OrderedDict[str, tuple[list[str], list[float]]] = OrderedDict()
        self._patterns = self._load_patterns()

    def _cache_set(self, key: str, value: list[str], embedding: list[float]):
        """Set cache entry with LRU eviction. Stores rewrites + query embedding."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, embedding)
        if len(self._cache) > _CACHE_MAX_SIZE:
            self._cache.popitem(last=False)

    def _cache_get(self, key: str) -> Optional[list[str]]:
        """Get cached rewrites if exists, move to end (LRU)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key][0]
        return None

    @property
    def client(self):
        """Lazy-load Minimax client only when needed."""
        if self._client is None:
            from ..llm.minimax import MinimaxClient
            self._client = MinimaxClient()
        return self._client

    @property
    def embed(self):
        """Lazy-load embedder."""
        if self.embedder is None:
            from ..embedder.aliyun_embedder import AliyunEmbedder
            self.embedder = AliyunEmbedder()
        return self.embedder

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-create shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http_client

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _find_similar_cache(self, query_embedding: list[float]) -> Optional[list[str]]:
        """Find cached entry with cosine similarity > threshold."""
        for key, (rewrites, cached_emb) in self._cache.items():
            if self._cosine_sim(query_embedding, cached_emb) > _SEMANTIC_THRESHOLD:
                self._cache.move_to_end(key)
                return rewrites
        return None

    def _load_patterns(self) -> list[tuple[str, list[str]]]:
        """Load expansion patterns from config file or use generic defaults."""
        default = [
            ("30m", ["30 m", "30米", "30 meters"]),
            ("50m", ["50 m", "50米", "50 meters"]),
            ("100m", ["100 m", "100米", "100 meters"]),
            ("km", ["千米", "公里", "kilometers"]),
            ("km/h", ["kmh", "kmph", "千米/小时", "公里/小时"]),
            ("m/s", ["米/秒", "meters per second"]),
            ("部署", ["deploy", "deployment", "上线", "release"]),
            ("安全", ["security", "安全策略", "权限"]),
            ("性能", ["performance", "效率", "优化", "metrics"]),
            ("监控", ["monitoring", "监控面板", "dashboard"]),
            ("日志", ["logs", "logging", "日志分析"]),
            ("API", ["api接口", "接口", "endpoint", "rest"]),
            ("用户", ["user", "用户管理", "users", "账户"]),
            ("权限", ["permission", "权限管理", "access control", "RBAC"]),
            ("配置", ["config", "settings", "configuration"]),
            ("备份", ["backup", "back up", "数据备份"]),
            ("恢复", ["recovery", "restore", "数据恢复"]),
            ("迁移", ["migration", "迁移", "transfer"]),
            ("集群", ["cluster", "集群", "distributed"]),
            ("容器", ["container", "docker", "容器化"]),
            ("RTO", ["Recovery Time Objective", "恢复时间目标", "故障恢复时间"]),
            ("RPO", ["Recovery Point Objective", "恢复点目标", "数据丢失容忍"]),
            ("Pending", ["等待", "待处理", "挂起"]),
            ("Pod", ["pod", "容器组", "kubernetes pod"]),
            ("failover", ["故障切换", "失效转移", "灾难恢复"]),
            ("API Gateway", ["api网关", "网关", "API gateway"]),
            ("Developer", ["开发者", "开发人员", "dev"]),
            ("告警", ["alert", "警报", "报警"]),
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

        Strategy:
        1. Check exact string cache
        2. Check semantic cache (embedding similarity > 0.95)
        3. LLM expansion
        4. Fallback to pattern expansion

        Args:
            user_query: Original user query string.

        Returns:
            List of query strings including the original and rewrites.
        """
        if not user_query or not user_query.strip():
            return [user_query]

        query_key = user_query.strip().lower()

        cached = self._cache_get(query_key)
        if cached:
            return cached

        try:
            query_embedding = await asyncio.to_thread(self.embed.embed, [user_query])
            query_embedding = query_embedding[0]

            similar = self._find_similar_cache(query_embedding)
            if similar:
                self._cache_set(query_key, similar, query_embedding)
                return similar
        except Exception:
            pass

        if len(user_query) < SHORT_QUERY_THRESHOLD:
            result = self._pattern_expand(user_query)
            try:
                emb = await asyncio.to_thread(self.embed.embed, [user_query])
                self._cache_set(query_key, result, emb[0])
            except Exception:
                pass
            return result

        prompt = f"{self.SYSTEM_PROMPT}\n\n原始查询：{user_query}"

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
                result = self._pattern_expand(user_query)
                self._cache_set(query_key, result, query_embedding)
                return result

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                result = self._pattern_expand(user_query)
                self._cache_set(query_key, result, query_embedding)
                return result

            content = choices[0].get("message", {}).get("content", "")
            rewrites = self._parse_rewrites(content)
            result = rewrites if rewrites else [user_query]
            self._cache_set(query_key, result, query_embedding)
            return result

        except Exception:
            result = self._pattern_expand(user_query)
            try:
                emb = await asyncio.to_thread(self.embed.embed, [user_query])
                self._cache_set(query_key, result, emb[0])
            except Exception:
                pass
            return result

    def _parse_rewrites(self, content: str) -> list[str]:
        """Parse LLM response into a list of query strings."""
        if not content:
            return []

        rewrites = [s.strip() for s in content.split("|")]
        rewrites = [s for s in rewrites if s and len(s) > 1]
        seen = set()
        unique = []
        for r in rewrites:
            norm = r.replace(" ", "").lower()
            if norm not in seen:
                seen.add(norm)
                unique.append(r)
        return unique

    async def rewrite_with_fallback(self, user_query: str) -> list[str]:
        """Rewrite with pattern expansion fallback when LLM fails."""
        rewrites = await self.rewrite(user_query)
        if len(rewrites) <= 1:
            rewrites = self._pattern_expand(user_query)
        return rewrites

    def _pattern_expand(self, query: str) -> list[str]:
        """Fallback pattern-based expansion using configurable generic rules."""
        expansions = [query]

        for original, variants in self._patterns:
            if original in query:
                for v in variants:
                    expanded = query.replace(original, v)
                    if expanded not in expansions:
                        expansions.append(expanded)

        return expansions[:5]

    def extract_prf_terms(self, retrieved_chunks: list[dict], min_freq: int = 2, top_n: int = 10) -> list[str]:
        """Extract top terms from retrieval results for PRF query expansion.

        Args:
            retrieved_chunks: List of retrieved chunk dicts with content
            min_freq: Minimum term frequency across top chunks to be included
            top_n: Maximum number of terms to return

        Returns:
            List of extracted terms for query expansion
        """
        import re
        from collections import Counter

        stop_words = {
            '的', '了', '和', '是', '在', '我', '有', '个', '人', '这',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
            'used', 'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'we', 'they', 'what', 'which', 'who', 'whom', 'where',
            'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'because', 'as', 'until',
            'while', 'of', 'for', 'with', 'about', 'against', 'between', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'from', 'up',
            'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
            'once', 'here', 'there', '如图', '所示', '因此', '但是', '然而',
            '并且', '或者', '如果', '则', '则', '即', '就是', '也就是',
        }

        term_counter = Counter()

        for chunk in retrieved_chunks[:5]:
            content = chunk.get('parent_content', '') or chunk.get('child_content', '') or ''
            words = re.findall(r'[\w\u4e00-\u9fff]{2,}', content.lower())
            filtered = [w for w in words if w not in stop_words and len(w) > 2]
            term_counter.update(filtered)

        significant_terms = [
            term for term, count in term_counter.most_common(50)
            if count >= min_freq
        ]

        return significant_terms[:top_n]

    async def close(self):
        """Close the underlying HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


async def rewrite_query(user_query: str) -> list[str]:
    """Convenience function for query rewriting."""
    rewriter = QueryRewriter()
    return await rewriter.rewrite_with_fallback(user_query)
