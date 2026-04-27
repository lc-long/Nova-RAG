"""Minimax m2.7 LLM client with native HTTP requests and SSE streaming."""
import os
import json
from typing import Generator, Optional
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str


@dataclass
class StreamChunk:
    content: str
    done: bool
    references: Optional[list[dict]] = None


class MinimaxClient:
    """Minimax m2.7 streaming client using native requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimax.chat/v1"

    def stream_chat(
        self,
        messages: list[Message],
        context_chunks: list[dict]
    ) -> Generator[StreamChunk, None, None]:
        """Stream chat completion with RAG context using SSE.

        Args:
            messages: Chat history
            context_chunks: Retrieved parent chunks for context

        Yields:
            StreamChunk with content, done flag, and references
        """
        context_text = self._build_context_prompt(context_chunks)
        prompt = self._build_prompt(messages, context_text)

        references = self._build_references(context_chunks)

        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "abab6.5s-chat",
            "group_id": self.group_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        response = requests.post(
            f"{self.base_url}/text/chatcompletion_v2",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"Minimax API error: {response.status_code} - {response.text}")

        # Use sseclient-py for proper SSE parsing
        from sseclient import SSEClient

        client = SSEClient(response)
        for event in client.events():
            # Skip empty data or [DONE] sentinel
            if not event.data or event.data.strip() == "[DONE]":
                continue

            try:
                data = json.loads(event.data)

                # Ensure data is a dict and choices exists
                if not isinstance(data, dict):
                    print(f"[Minimax] Warning: received non-dict data: {type(data)}")
                    continue

                choices = data.get("choices")
                if not choices or not isinstance(choices, list) or len(choices) == 0:
                    print(f"[Minimax] Warning: choices missing or empty in data: {data}")
                    continue

                delta = choices[0].get("delta", {})
                if not isinstance(delta, dict):
                    print(f"[Minimax] Warning: delta is not a dict: {type(delta)}")
                    continue

                content = delta.get("content", "")
                if content:
                    yield StreamChunk(
                        content=content,
                        done=False,
                        references=None
                    )
            except json.JSONDecodeError:
                # Skip malformed JSON (e.g., partial data)
                print(f"[Minimax] Warning: JSON decode failed for: {event.data[:100]}")
                continue
            except Exception as e:
                print(f"[Minimax] Warning: Unexpected error processing event: {e}")
                continue

        yield StreamChunk(content="", done=True, references=references)

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
        return f"""你是一个企业知识库助手。请严格根据提供的上下文信息回答用户问题。
如果上下文中没有相关信息，请明确告知用户"抱歉，我在知识库中未找到相关内容"。

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