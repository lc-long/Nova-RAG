"""LLM client with MiniMax primary + DeepSeek fallback, async SSE streaming."""
import os
import json
import logging
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

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimaxi.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

        # DeepSeek fallback
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek = DeepSeekClient(deepseek_key) if deepseek_key else None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self._client

    async def stream_chat(
        self,
        messages: list[Message],
        context_chunks: list[dict]
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat with MiniMax, fallback to DeepSeek on failure."""
        # Try MiniMax first
        try:
            async for chunk in self._stream_minimax(messages, context_chunks):
                yield chunk
            return  # Success, no need for fallback
        except Exception as e:
            logger.warning(f"[LLM] MiniMax failed: {e}, trying DeepSeek...")

        # Fallback to DeepSeek
        if self.deepseek:
            try:
                async for chunk in self.deepseek.stream_chat(
                    messages, context_chunks, self, self._build_references
                ):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"[LLM] DeepSeek also failed: {e}")
                raise Exception(f"Both MiniMax and DeepSeek failed. Last error: {e}")

        raise Exception(f"MiniMax failed and no DeepSeek API key configured: {e}")

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
        return f"""你是一个严谨的企业知识库助手。请根据提供的上下文信息回答用户问题。
如果上下文中有任何与用户问题相关的信息（即使不是完全匹配），请基于这些信息回答。
只有当上下文中完全没有相关信息时，才告知用户"抱歉，我在知识库中未找到相关内容"。

请特别注意：
1. 用户的问题可能在文档中有**多个不同场景的答案**（例如不同的飞行模式、不同的操作条件、不同的地区规定）。
2. 请务必仔细阅读所有提供的上下文片段，提取出**所有符合条件**的场景并分点列出，绝不能只回答第一个找到的场景就停止。
3. 如果上下文中没有提及某个具体数值（如限制距离50m），请明确指出"该部分信息缺失"，不要编造。
4. 回答时必须分场景/条件逐一列举，不要混在一起回答。
5. **条件调整规则**：如果上下文中有基础值和调整规则（例如"最大高度120米，风速超过8m/s时降低30%"），你必须同时找到两者并应用调整规则计算最终结果。不要只回答基础值而忽略调整规则。
6. **否定推理**：如果文档明确列出了允许的条件（例如"仅限X-500和X-700"），那么未列出的型号就是不允许的。请直接给出否定结论。
7. **版本对比**：如果文档提到某个规定在新版本中有调整，请注意区分新旧版本的不同规定，以最新版本为准。
8. **跨语言匹配**：用户的查询可能是中文，而文档内容可能是英文（或反之）。请理解中英文之间的对应关系（如"饼状图"="pie chart"，"Revenue Distribution"="收入分布"）。
9. **不要猜测图表类型**：文档中的数据（如数值列表、产品名称）可能是从图表中提取的原始数据。不要根据数值格式猜测图表类型（如柱状图、饼状图等）。如果文档没有明确说明图表类型，请如实告知用户"文档中包含相关数据，但未明确标注图表类型"。
10. **如实回答**：如果文档中有与用户问题相关的信息，即使不是完全匹配，也要如实呈现文档中的内容，并说明文档中实际包含的信息。

## 上下文信息
{context}

## 对话历史
{history}

## 用户问题"""

    def _build_references(self, chunks: list[dict]) -> list[dict]:
        references = []
        for i, chunk in enumerate(chunks, 1):
            references.append({
                "index": i,
                "doc_id": chunk.get("doc_id", "Unknown"),
                "source_doc": chunk.get("doc_id", "Unknown"),
                "page_number": chunk.get("page_number", 0),
                "content": chunk.get("parent_content", "")[:200]
            })
        return references
