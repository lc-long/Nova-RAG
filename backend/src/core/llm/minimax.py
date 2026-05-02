"""Minimax m2.7 LLM client with async HTTP and SSE streaming."""
import os
import json
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

import httpx


@dataclass
class Message:
    role: str
    content: str


@dataclass
class StreamChunk:
    chunk_type: str  # "reasoning" | "answer" | "done"
    content: str
    references: Optional[list[dict]] = None


class MinimaxClient:
    """Minimax m2.7 async streaming client using httpx."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimaxi.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-create shared async HTTP client (connection pooling)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self._client

    async def stream_chat(
        self,
        messages: list[Message],
        context_chunks: list[dict]
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completion with RAG context using async SSE.

        Args:
            messages: Chat history
            context_chunks: Retrieved parent chunks for context

        Yields:
            StreamChunk with chunk_type ("reasoning"|"answer"|"done"), content, and references
        """
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

        try:
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

                        choices = data.get("choices")
                        if not choices or not isinstance(choices, list) or len(choices) == 0:
                            continue

                        choice = choices[0]
                        delta = choice.get("delta", {})
                        if not isinstance(delta, dict):
                            continue

                        reasoning = delta.get("reasoning_content", "")
                        content = delta.get("content", "")

                        if reasoning:
                            yield StreamChunk(
                                chunk_type="reasoning",
                                content=reasoning,
                                references=None
                            )

                        if content:
                            yield StreamChunk(
                                chunk_type="answer",
                                content=content,
                                references=None
                            )

                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            yield StreamChunk(chunk_type="done", content="", references=references)
                            return

                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue

        except httpx.HTTPError as e:
            raise Exception(f"Minimax API connection error: {e}")

        yield StreamChunk(chunk_type="done", content="", references=references)

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _build_context_prompt(self, chunks: list[dict]) -> str:
        """Build context section of prompt with [N] citation format."""
        if not chunks:
            return "No relevant documents found."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_id = chunk.get("doc_id", "Unknown")
            content = chunk.get("parent_content", chunk.get("child_content", ""))
            context_parts.append(f"[{i}] Document: {doc_id}\n{content}")

        return "\n\n---\n\n".join(context_parts)

    def _build_prompt(self, messages: list[Message], context: str) -> str:
        """Build full prompt with context and messages."""
        history = "\n".join([f"{m.role}: {m.content}" for m in messages])
        return f"""你是一个严谨的企业知识库助手。请严格根据提供的上下文信息回答用户问题。
如果上下文中没有相关信息，请明确告知用户"抱歉，我在知识库中未找到相关内容"。

请特别注意：
1. 用户的问题可能在文档中有**多个不同场景的答案**（例如不同的飞行模式、不同的操作条件、不同的地区规定）。
2. 请务必仔细阅读所有提供的上下文片段，提取出**所有符合条件**的场景并分点列出，绝不能只回答第一个找到的场景就停止。
3. 如果上下文中没有提及某个具体数值（如限制距离50m），请明确指出"该部分信息缺失"，不要编造。
4. 回答时必须分场景/条件逐一列举，不要混在一起回答。
5. **条件调整规则**：如果上下文中有基础值和调整规则（例如"最大高度120米，风速超过8m/s时降低30%"），你必须同时找到两者并应用调整规则计算最终结果。不要只回答基础值而忽略调整规则。
6. **否定推理**：如果文档明确列出了允许的条件（例如"仅限X-500和X-700"），那么未列出的型号就是不允许的。请直接给出否定结论。
7. **版本对比**：如果文档提到某个规定在新版本中有调整，请注意区分新旧版本的不同规定，以最新版本为准。

## 上下文信息
{context}

## 对话历史
{history}

## 用户问题"""

    def _build_references(self, chunks: list[dict]) -> list[dict]:
        """Build references list WITHOUT <cite> tags - using [N] format."""
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
