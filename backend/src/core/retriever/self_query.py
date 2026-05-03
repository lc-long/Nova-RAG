"""Self-Query Retriever: Parse user query into semantic + metadata filters.

Self-Query decomposes a natural language query into:
1. Semantic query - the core question for vector search
2. Metadata filters - structured conditions (doc name, time, author, etc.)

Example:
  User: "2025年鸭鸭的用户报告"
  → Semantic: "用户报告"
  → Metadata: author=鸭鸭, year=2025
"""
import json
import os
import logging
import re
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("nova_rag")


@dataclass
class MetadataFilter:
    """Structured metadata filter extracted from query."""
    doc_name_pattern: Optional[str] = None  # Filename pattern to match
    page_range: Optional[tuple[int, int]] = None  # (start_page, end_page)
    semantic_query: str = ""  # The core semantic query


@dataclass
class SelfQueryResult:
    """Result of self-query parsing."""
    original_query: str
    semantic_query: str
    filters: MetadataFilter
    raw_llm_response: str = ""


SYSTEM_PROMPT = """You are a query parsing expert. Extract document filtering conditions from user queries.

Output JSON format:
{
  "semantic_query": "core question without filters",
  "doc_name": "document name keyword (if any)",
  "page_range": [start_page, end_page] or null
}

Examples:
User: "2025年鸭鸭的用户报告"
→ {"semantic_query": "用户报告内容", "doc_name": "鸭鸭", "page_range": null}

User: "第3页的图表是什么意思"
→ {"semantic_query": "图表是什么意思", "doc_name": null, "page_range": [3, 3]}

User: "nova tech文档中的架构图"
→ {"semantic_query": "架构图", "doc_name": "nova tech", "page_range": null}

User: "explain the multi-region deployment"
→ {"semantic_query": "multi-region deployment architecture", "doc_name": null, "page_range": null}

User: "what happens when one zone goes down?"
→ {"semantic_query": "zone failure failover mechanism", "doc_name": null, "page_range": null}

Note:
- Only extract conditions explicitly mentioned by user
- If no filters mentioned, set doc_name and page_range to null
- semantic_query should preserve full user intent"""


class SelfQueryRetriever:
    """Parse user queries into semantic + metadata components using LLM."""

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http_client

    async def parse_query(self, user_query: str) -> SelfQueryResult:
        """Parse user query into semantic query + metadata filters."""
        # Fast path: if query is short and has no obvious filter keywords, skip LLM
        if len(user_query) < 15 and not self._has_filter_hints(user_query):
            return SelfQueryResult(
                original_query=user_query,
                semantic_query=user_query,
                filters=MetadataFilter(semantic_query=user_query),
            )

        try:
            result = await self._llm_parse(user_query)
            return result
        except Exception as e:
            logger.warning(f"[SelfQuery] LLM parse failed: {e}, using original query")
            return SelfQueryResult(
                original_query=user_query,
                semantic_query=user_query,
                filters=MetadataFilter(semantic_query=user_query),
            )

    def _has_filter_hints(self, query: str) -> bool:
        """Quick check if query likely contains metadata filter hints."""
        hints = [
            r'\d{4}年',  # Year
            r'第\d+页',  # Page number
            r'文档[名叫]',  # Document name reference
            r'来源',  # Source
        ]
        return any(re.search(h, query) for h in hints)

    async def _llm_parse(self, user_query: str) -> SelfQueryResult:
        """Use LLM to parse query into structured components."""
        # Try DeepSeek first (cheaper and more available)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            try:
                return await self._parse_with_deepseek(user_query, deepseek_key)
            except Exception as e:
                logger.warning(f"[SelfQuery] DeepSeek failed: {e}")

        # Fallback to MiniMax
        minimax_key = os.getenv("MINIMAX_API_KEY", "")
        if minimax_key:
            try:
                return await self._parse_with_minimax(user_query, minimax_key)
            except Exception as e:
                logger.warning(f"[SelfQuery] MiniMax failed: {e}")

        # Final fallback: return original query
        return SelfQueryResult(
            original_query=user_query,
            semantic_query=user_query,
            filters=MetadataFilter(semantic_query=user_query),
        )

    async def _parse_with_deepseek(self, query: str, api_key: str) -> SelfQueryResult:
        """Parse query using DeepSeek API."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"用户问题：{query}"},
            ],
            "stream": False,
            "temperature": 0,
        }

        resp = await self.http_client.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload, headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return self._parse_llm_response(query, content)

    async def _parse_with_minimax(self, query: str, api_key: str) -> SelfQueryResult:
        """Parse query using MiniMax API."""
        group_id = os.getenv("MINIMAX_GROUP_ID", "")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "MiniMax-M2.7",
            "group_id": group_id,
            "messages": [
                {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n用户问题：{query}"},
            ],
            "stream": False,
        }

        resp = await self.http_client.post(
            "https://api.minimaxi.com/v1/text/chatcompletion_v2",
            json=payload, headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return self._parse_llm_response(query, content)

    def _parse_llm_response(self, original_query: str, llm_output: str) -> SelfQueryResult:
        """Parse LLM JSON output into SelfQueryResult."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = llm_output
        if "```" in json_str:
            match = re.search(r'```(?:json)?\s*(.*?)```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1).strip()

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"[SelfQuery] Failed to parse LLM output as JSON: {llm_output[:200]}")
            return SelfQueryResult(
                original_query=original_query,
                semantic_query=original_query,
                filters=MetadataFilter(semantic_query=original_query),
                raw_llm_response=llm_output,
            )

        semantic_query = parsed.get("semantic_query", original_query)
        doc_name = parsed.get("doc_name")
        page_range = parsed.get("page_range")

        filters = MetadataFilter(
            semantic_query=semantic_query,
            doc_name_pattern=doc_name if doc_name else None,
            page_range=tuple(page_range) if page_range and len(page_range) == 2 else None,
        )

        logger.info(f"[SelfQuery] '{original_query}' → semantic='{semantic_query}', doc={doc_name}, page={page_range}")

        return SelfQueryResult(
            original_query=original_query,
            semantic_query=semantic_query,
            filters=filters,
            raw_llm_response=llm_output,
        )

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
