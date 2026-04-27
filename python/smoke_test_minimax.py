"""Smoke test for Minimax SSE streaming - verifies real API connectivity."""
import os

# Load .env before any other imports
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

print("=" * 60)
print("Minimax SSE Streaming Smoke Test")
print("=" * 60)

print(f"[Config] MINIMAX_API_KEY set: {bool(os.getenv('MINIMAX_API_KEY'))}")
print(f"[Config] MINIMAX_GROUP_ID set: {bool(os.getenv('MINIMAX_GROUP_ID'))}")

from src.core.llm.minimax import MinimaxClient, Message

# Test raw response
import requests

client = MinimaxClient()
print(f"[Client] Base URL: {client.base_url}")

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

# Non-streaming test first
print("\n[Non-streaming Test] Single shot...")
non_resp = requests.post(
    f"{client.base_url}/text/chatcompletion_v2",
    headers=headers,
    json={**payload, "stream": False},
    timeout=30
)
print(f"[Non-streaming] Status: {non_resp.status_code}")
print(f"[Non-streaming] Body: {non_resp.text[:400]}")

print("\n[Raw Test] Fetching raw SSE from API...")
response = requests.post(
    f"{client.base_url}/text/chatcompletion_v2",
    headers=headers,
    json=payload,
    stream=True,
    timeout=60
)

print(f"[Raw] Status: {response.status_code}")

for i, line in enumerate(response.iter_lines()):
    if not line:
        continue
    decoded = line.decode('utf-8', errors='replace')
    print(f"  [line {i:3d}] {decoded}")
    if i > 50:
        print("  ... (truncated)")
        break

response.close()

print("\n[Stream Test] Testing via MinimaxClient.stream_chat...")
messages = [Message(role="user", content="你好，介绍你自己")]
print("-" * 40)

for i, chunk in enumerate(client.stream_chat(messages, [])):
    if chunk.content:
        print(f"  [{i}] {chunk.content[:100]}")
    else:
        print(f"  [{i}] done=True, refs={chunk.references is not None}")

print("-" * 40)
print("[Done]")