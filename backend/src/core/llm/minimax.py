"""LLM client with MiniMax primary + DeepSeek fallback, async SSE streaming."""
import os
import json
import asyncio
import logging
from collections import OrderedDict
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger("nova_rag")


@dataclass
class Message:
    role: str
    content: str


@dataclass
class StreamChunk:
    chunk_type: str  # "reasoning" | "answer" | "done"
    content: str
    references: Optional[list[dict]] = None


class DeepSeekClient:
    """DeepSeek async streaming client (OpenAI-compatible API)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self._client

    async def stream_chat(
        self,
        messages: list[Message],
        context_chunks: list[dict],
        prompt_builder,
        references_builder,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat using DeepSeek API."""
        context_text = prompt_builder._build_context_prompt(context_chunks)
        prompt = prompt_builder._build_prompt(messages, context_text)
        references = references_builder(context_chunks)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise Exception(f"DeepSeek API error: {response.status_code} - {body.decode()}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield StreamChunk(chunk_type="answer", content=content, references=None)

                        finish_reason = choices[0].get("finish_reason")
                        if finish_reason:
                            yield StreamChunk(chunk_type="done", content="", references=references)
                            return

                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPError as e:
            raise Exception(f"DeepSeek API connection error: {e}")

        yield StreamChunk(chunk_type="done", content="", references=references)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class MinimaxClient:
    """LLM client with MiniMax primary + DeepSeek fallback."""

    RESPONSE_CACHE_MAX_SIZE = 256
    RESPONSE_CACHE_THRESHOLD = 0.95

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimaxi.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

        self._response_cache: OrderedDict[str, tuple[str, list[dict], list[float]]] = OrderedDict()
        self._embedder: Optional[object] = None

# DeepSeek fallback
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek = DeepSeekClient(deepseek_key) if deepseek_key else None

    @property
    def embedder(self):
        """Lazy-load embedder for response cache."""
        if self._embedder is None:
            from ..embedder.aliyun_embedder import AliyunEmbedder
            self._embedder = AliyunEmbedder()
        return self._embedder

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _cache_response_set(self, key: str, answer: str, references: list[dict], embedding: list[float]):
        """Set response cache entry with LRU eviction."""
        if key in self._response_cache:
            self._response_cache.move_to_end(key)
        self._response_cache[key] = (answer, references, embedding)
        if len(self._response_cache) > self.RESPONSE_CACHE_MAX_SIZE:
            self._response_cache.popitem(last=False)

    def _cache_response_get(self, key: str) -> Optional[tuple[str, list[dict]]]:
        """Get cached response if exists."""
        if key in self._response_cache:
            self._response_cache.move_to_end(key)
            return self._response_cache[key][:2]
        return None

    def _find_similar_response(self, query_embedding: list[float]) -> Optional[tuple[str, list[dict]]]:
        """Find cached response with cosine similarity > threshold."""
        for key, (answer, refs, cached_emb) in self._response_cache.items():
            if self._cosine_sim(query_embedding, cached_emb) > self.RESPONSE_CACHE_THRESHOLD:
                self._response_cache.move_to_end(key)
                return answer, refs
        return None

    async def stream_chat(
        self,
        messages: list[Message],
        context_chunks: list[dict]
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat with MiniMax, fallback to DeepSeek on failure.

        Uses response cache with semantic similarity (cosine > 0.95) to skip LLM calls.
        """
        last_query = messages[-1].content if messages else ""
        cache_key = last_query.strip().lower()

        try:
            query_embedding = await asyncio.to_thread(self.embedder.embed, [last_query])
            query_embedding = query_embedding[0]

            cached = self._find_similar_response(query_embedding)
            if cached:
                logger.info(f"[LLM] Response cache hit for query: {last_query[:50]}...")
                answer_text, cached_refs = cached
                for char in answer_text:
                    yield StreamChunk(chunk_type="answer", content=char, references=None)
                yield StreamChunk(chunk_type="done", content="", references=cached_refs)
                return
        except Exception:
            pass

        full_answer = ""
        result_refs = None

        async def generate():
            nonlocal full_answer, result_refs
            try:
                async for chunk in self._stream_minimax(messages, context_chunks):
                    yield chunk
                    if chunk.chunk_type == "done":
                        result_refs = chunk.references
                    elif chunk.chunk_type == "answer":
                        full_answer += chunk.content
            except Exception as e:
                logger.warning(f"[LLM] MiniMax failed: {e}, trying DeepSeek...")

                if self.deepseek:
                    try:
                        async for chunk in self.deepseek.stream_chat(
                            messages, context_chunks, self, self._build_references
                        ):
                            yield chunk
                            if chunk.chunk_type == "done":
                                result_refs = chunk.references
                            elif chunk.chunk_type == "answer":
                                full_answer += chunk.content
                        return
                    except Exception as e:
                        logger.error(f"[LLM] DeepSeek also failed: {e}")
                        raise Exception(f"Both MiniMax and DeepSeek failed. Last error: {e}")

                raise Exception(f"MiniMax failed and no DeepSeek API key configured: {e}")

        try:
            async for chunk in generate():
                yield chunk
        finally:
            if full_answer and result_refs is not None:
                try:
                    self._cache_response_set(cache_key, full_answer, result_refs, query_embedding)
                except Exception:
                    pass

    async def _stream_minimax(
        self,
        messages: list[Message],
        context_chunks: list[dict]
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat using MiniMax API."""
        context_text = self._build_context_prompt(context_chunks)
        prompt = self._build_prompt(messages, context_text)
        references = self._build_references(context_chunks)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "MiniMax-M2.7",
            "group_id": self.group_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        got_content = False

        async with self.client.stream(
            "POST",
            f"{self.base_url}/text/chatcompletion_v2",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise Exception(f"Minimax API error: {response.status_code} - {body.decode()}")

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue

                try:
                    data = json.loads(data_str)
                    if not isinstance(data, dict):
                        continue

                    # Check for API errors (usage limit, etc.)
                    base_resp = data.get("base_resp", {})
                    if isinstance(base_resp, dict) and base_resp.get("status_code", 0) != 0:
                        raise Exception(f"MiniMax API error: {base_resp.get('status_msg', 'unknown')}")

                    choices = data.get("choices")
                    if not choices or not isinstance(choices, list) or len(choices) == 0:
                        # Empty choices might mean usage limit exceeded
                        continue

                    choice = choices[0]
                    delta = choice.get("delta", {})
                    if not isinstance(delta, dict):
                        continue

                    reasoning = delta.get("reasoning_content", "")
                    content = delta.get("content", "")

                    if reasoning:
                        got_content = True
                        yield StreamChunk(chunk_type="reasoning", content=reasoning, references=None)
                    if content:
                        got_content = True
                        yield StreamChunk(chunk_type="answer", content=content, references=None)

                    finish_reason = choice.get("finish_reason")
                    if finish_reason:
                        yield StreamChunk(chunk_type="done", content="", references=references)
                        return

                except json.JSONDecodeError:
                    continue

        if not got_content:
            raise Exception("MiniMax returned no content (possibly usage limit exceeded)")

        yield StreamChunk(chunk_type="done", content="", references=references)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self.deepseek:
            await self.deepseek.close()

    def _build_context_prompt(self, chunks: list[dict]) -> str:
        if not chunks:
            return "No relevant documents found."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_id = chunk.get("doc_id", "Unknown")
            content = chunk.get("parent_content", chunk.get("child_content", ""))
            context_parts.append(f"[{i}] Document: {doc_id}\n{content}")

        return "\n\n---\n\n".join(context_parts)

    def _build_prompt(self, messages: list[Message], context: str) -> str:
        history = "\n".join([f"{m.role}: {m.content}" for m in messages])

        few_shot = """示例对话：

用户问题：你们的服务器配置有什么选项？
回答：
根据文档，服务器配置选项如下：
1. **基础型**：2核4G内存，适用于小型应用
2. **标准型**：4核8G内存，适用于中型应用
3. **高级型**：8核16G内存，适用于大型应用
（文档中未提及具体价格信息，该部分内容缺失）

用户问题：采购流程是什么？
回答：
根据文档，采购流程如下：
1. **提交申请**：在系统中填写采购申请表
2. **部门审批**：直属上级审批通过后进入下一阶段
3. **财务复核**：财务部门进行预算复核
4. **执行采购**：采购部门执行采购操作

用户问题：某个功能如何配置？
回答：
根据文档，该功能配置步骤如下：
1. 进入系统设置页面
2. 找到对应的功能模块
3. 根据实际需求调整参数
（文档中未包含截图或操作示意，如需更详细的指导请联系管理员）"""

        return f"""你是一个严谨的企业知识库助手。请根据提供的上下文信息回答用户问题。
如果上下文中有任何与用户问题相关的信息（即使不是完全匹配），请基于这些信息回答。
只有当上下文中完全没有相关信息时，才告知用户"抱歉，我在知识库中未找到相关内容"。

请注意以下规则：
1. **多场景分点**：如果文档中存在多个相关场景/条件/情况，必须逐一列举，不能只回答第一个
2. **数据缺失处理**：如果文档缺少某些具体数值、参数或细节，明确说明"该部分信息缺失"，不要猜测或编造
3. **否定回答**：如果文档明确说明某项内容不适用、不允许或不存在，直接给出否定结论
4. **版本/时间区分**：如果文档提到不同时期/版本的规定，以最新版本为准
5. **跨语言理解**：用户用中文问，文档可能是英文（或反之），理解中英文对应关系
6. **图表说明**：如果文档数据来自图表但未明确图表类型，直接描述数据而非猜测图表类型
7. **如实呈现**：基于文档内容回答，不要添加文档中没有的信息
8. **表格数据必须核实**：如果上下文包含表格数据（标记为"--- 表格数据开始 ---"），回答中的数字必须来自表格，严禁编造；如果表格中没有某个单元格的数据，明确说明"表格中该数据缺失"
9. **避免幻觉**：如果不确定某个信息是否在文档中，明确说明"我未在文档中找到相关内容"，不要凭记忆猜测
10. **严格归因**：每个陈述必须能追溯到上下文中的具体来源，如果某个信息在上下文中没有明确支持，必须明确说明"该信息未在文档中找到"
11. **禁止推断**：不要基于文档中的部分信息进行推断或假设，只能陈述文档中明确说明的内容

{few_shot}

## 上下文信息
{context}

## 对话历史
{history}

## 用户问题"""

    def _build_references(self, chunks: list[dict]) -> list[dict]:
        references = []
        for i, chunk in enumerate(chunks, 1):
            distance = chunk.get("distance", 1.0)
            vector_score = 1.0 - distance if distance <= 1.0 else 0.5
            bm25_score = chunk.get("bm25_score", 0.0)
            rerank_score = chunk.get("rerank_score", 0.0)
            combined_score = 0.7 * vector_score + 0.3 * (bm25_score / 10.0) if bm25_score else vector_score
            if rerank_score > 0:
                combined_score = rerank_score
            metadata = chunk.get("metadata_", {}) or {}
            references.append({
                "index": i,
                "doc_id": chunk.get("doc_id", "Unknown"),
                "source_doc": metadata.get("source", chunk.get("doc_id", "Unknown")),
                "page_number": chunk.get("page_number", 0),
                "content": chunk.get("parent_content", "")[:200],
                "score": round(combined_score, 3),
                "score_type": "rerank" if rerank_score > 0 else ("combined" if bm25_score else "vector"),
                "vector_score": round(vector_score, 3),
                "bm25_score": round(bm25_score, 3) if bm25_score else None,
                "chunk_index": metadata.get("order", i),
                "parent_chunk_index": chunk.get("parent_id", ""),
            })
        return references
