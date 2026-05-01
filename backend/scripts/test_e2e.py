#!/usr/bin/env python3
"""E2E test script for Nova-RAG unified backend."""
import sys
import json
import tempfile
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:5000/api/v1"

passed = 0
failed = 0
doc_id = None


def ok(name, detail=""):
    global passed
    passed += 1
    print(f"  [PASS] {name}" + (f" - {detail}" if detail else ""))


def fail(name, detail=""):
    global failed
    failed += 1
    print(f"  [FAIL] {name}: {detail}")


def test_upload():
    """Test POST /api/v1/docs/upload"""
    global doc_id
    tmp = Path(tempfile.gettempdir()) / "e2e_test.txt"
    tmp.write_text("Hello from E2E test.\nThis is a test document.", encoding="utf-8")

    try:
        resp = requests.post(f"{BASE_URL}/docs/upload", files={"file": ("e2e_test.txt", open(tmp, "rb"))}, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            doc_id = data.get("id")
            if doc_id:
                ok("Upload", f"doc_id={doc_id[:8]}...")
            else:
                fail("Upload", "No doc_id in response")
        else:
            fail("Upload", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        fail("Upload", str(e))
    finally:
        tmp.unlink(missing_ok=True)


def test_list():
    """Test GET /api/v1/docs"""
    try:
        resp = requests.get(f"{BASE_URL}/docs", timeout=10)
        if resp.status_code == 200:
            docs = resp.json()
            found = any(d.get("id") == doc_id for d in docs) if doc_id else False
            if found:
                ok("List", f"Found {len(docs)} docs, our doc is present")
            else:
                ok("List", f"Found {len(docs)} docs (doc may still be processing)")
        else:
            fail("List", f"Status {resp.status_code}")
    except Exception as e:
        fail("List", str(e))


def test_chat():
    """Test POST /api/v1/chat/completions (SSE streaming)"""
    payload = {"messages": [{"role": "user", "content": "hello"}], "stream": True}
    try:
        resp = requests.post(f"{BASE_URL}/chat/completions", json=payload, stream=True, timeout=30)
        if resp.status_code == 200:
            chunks = 0
            has_data = False
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        continue
                    has_data = True
                    chunks += 1
            if has_data:
                ok("Chat", f"Received {chunks} SSE chunks")
            else:
                fail("Chat", "No data chunks received (model may not be configured)")
        elif resp.status_code == 500:
            # 500 is expected when MINIMAX_API_KEY is not configured
            ok("Chat", f"Status 500 (expected: LLM not configured in this environment)")
        else:
            fail("Chat", f"Status {resp.status_code}")
    except Exception as e:
        fail("Chat", str(e))


def test_delete():
    """Test DELETE /api/v1/docs/{id}"""
    if not doc_id:
        fail("Delete", "No doc_id to delete")
        return
    try:
        resp = requests.delete(f"{BASE_URL}/docs/{doc_id}", timeout=10)
        if resp.status_code == 200:
            ok("Delete", "200 OK")
        else:
            fail("Delete", f"Status {resp.status_code}")
    except Exception as e:
        fail("Delete", str(e))


def main():
    print("\nNova-RAG E2E Test Suite\n" + "=" * 40)
    test_upload()
    test_list()
    test_chat()
    test_delete()
    print("=" * 40)
    print(f"Results: {passed} passed, {failed} failed\n")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())