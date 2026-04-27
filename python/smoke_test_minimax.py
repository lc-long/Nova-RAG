"""Smoke test for Minimax SSE streaming - simulates Python-side validation."""
import os
import sys
import json

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("=" * 60)
print("Minimax SSE Streaming Smoke Test")
print("=" * 60)

from src.core.llm.minimax import MinimaxClient, Message

# Test raw response first
import requests

client = MinimaxClient()
headers = {
    "Authorization": f"Bearer {client.api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "minimax-text-01",
    "group_id": client.group_id,
    "messages": [{"role": "user", "content": "你好，介绍你自己"}],
    "stream": True
}

print("\n[Raw Test] Fetching raw SSE from API...")
response = requests.post(
    f"{client.base_url}/text/chatcompletion_v2",
    headers=headers,
    json=payload,
    stream=True,
    timeout=60
)

print(f"[Raw] Status: {response.status_code}")
print("[Raw] First 5 lines:")
for i, line in enumerate(response.iter_lines()):
    if i >= 10:
        print("  ...")
        break
    print(f"  [{i}] {line[:120]}")

response.close()

print("\n[Smoke Test] Testing via MinimaxClient.stream_chat...")
messages = [Message(role="user", content="你好，介绍你自己")]
context_chunks = []
print("-" * 40)

for i, chunk in enumerate(client.stream_chat(messages, context_chunks)):
    if chunk.content:
        print(f"[{i}] content: {chunk.content[:80]}...")
    else:
        print(f"[{i}] done=True, references={chunk.references is not None}")

print("-" * 40)
print("[Smoke Test] Stream completed")