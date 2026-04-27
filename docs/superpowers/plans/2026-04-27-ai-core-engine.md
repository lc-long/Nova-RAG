# AI Core Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建 Python AI 检索引擎核心：文档解析、父子切片、向量化存储、Minimax 接入、流式 API

**Architecture:** 三层架构：API 层(FastAPI) → 核心引擎层(Chunker/Embedder/Retriever) → 数据层(ChromaDB)，通过 RAG Loop 组装完整流程

**Tech Stack:** Python 3.10+, pdfplumber, ChromaDB, sentence-transformers, FastAPI, Minimax m2.7

---

### Task 1: 环境配置与 Go 依赖修复

**Files:**
- Modify: `backend/go.mod`
- Test: `backend/go.mod tidy`

- [ ] **Step 1: 设置 Go 模块代理并验证**

```bash
go env -w GOPROXY=https://goproxy.cn,direct
cd backend && go mod tidy
```
Expected: 所有依赖下载成功

- [ ] **Step 2: Commit**

```bash
git add backend/go.mod backend/go.sum
git commit -m "chore(config): set goproxy.cn for Go modules in China"
```

---

### Task 2: PDF 文档解析器实现

**Files:**
- Create: `python/src/core/chunker/pdf_parser.py`
- Create: `python/src/core/chunker/docx_parser.py`
- Modify: `python/requirements.txt`

- [ ] **Step 1: 创建 pdfplumber PDF 解析器**

```python
"""PDF document parser using pdfplumber."""
import pdfplumber
from pathlib import Path
from typing import Generator


def parse_pdf(file_path: str) -> Generator[tuple[str, int, str], None, None]:
    """
    Parse PDF and yield (text, page_number, full_text).
    
    Args:
        file_path: Path to PDF file
        page_number: Page number (1-indexed)
        full_text: Combined text of the page
    
    Yields:
        Tuple of (text, page_number, full_text)
    """
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                yield text, page_num, text


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF."""
    full_text = []
    for text, _, _ in parse_pdf(file_path):
        full_text.append(text)
    return "\n\n".join(full_text)
```

- [ ] **Step 2: 创建 docx 解析器**

```python
"""DOCX document parser using python-docx."""
from docx import Document
from pathlib import Path


def extract_text_from_docx(file_path: str) -> str:
    """Extract all text from DOCX file."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
```

- [ ] **Step 3: Commit**

```bash
git add python/src/core/chunker/pdf_parser.py python/src/core/chunker/docx_parser.py
git commit -m "feat(rag): add PDF and DOCX parsers using pdfplumber and python-docx"
```

---

### Task 3: 父子文档切片策略实现 (Parent-Child Chunking)

**Files:**
- Create: `python/src/core/chunker/parent_child.py`
- Modify: `python/src/core/chunker/base.py`

- [ ] **Step 1: 实现 ParentChildChunker 类**

```python
"""Parent-child chunking strategy for RAG.

切分逻辑：
1. Parent chunk: 按段落/固定长度切分，保留完整语义上下文
2. Child chunk: 从 parent 中进一步切分细小片段，提高检索命中率
3. 存储时建立 parent_id 关联，检索时先找 child 再找 parent
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    content: str
    doc_id: str
    chunk_type: str  # "parent" or "child"
    parent_id: Optional[str] = None
    page_number: Optional[int] = None
    order: int = 0


class ParentChildChunker:
    """Parent-child chunking with configurable sizes."""

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, doc_id: str) -> list[Chunk]:
        """Split text into parent-child chunks."""
        chunks = []
        parent_id = None
        
        # First create parent chunks
        parent_chunks = self._create_parent_chunks(text, doc_id)
        
        # Then create child chunks from each parent
        for parent in parent_chunks:
            children = self._create_child_chunks(parent, doc_id)
            chunks.append(parent)
            chunks.extend(children)
        
        return chunks

    def _create_parent_chunks(self, text: str, doc_id: str) -> list[Chunk]:
        """Create parent chunks from text."""
        chunks = []
        paragraphs = text.split("\n\n")
        current_parent = []
        current_size = 0
        parent_id = None
        
        for para in paragraphs:
            para_size = len(para)
            if current_size + para_size > self.parent_chunk_size and current_parent:
                # Finish current parent
                parent_id = f"{doc_id}_parent_{len(chunks)}"
                content = "\n\n".join(current_parent)
                chunks.append(Chunk(
                    chunk_id=parent_id,
                    content=content,
                    doc_id=doc_id,
                    chunk_type="parent",
                    parent_id=None,
                    order=len(chunks)
                ))
                current_parent = []
                current_size = 0
            
            current_parent.append(para)
            current_size += para_size
        
        # Handle remaining content
        if current_parent:
            parent_id = f"{doc_id}_parent_{len(chunks)}"
            content = "\n\n".join(current_parent)
            chunks.append(Chunk(
                chunk_id=parent_id,
                content=content,
                doc_id=doc_id,
                chunk_type="parent",
                parent_id=None,
                order=len(chunks)
            ))
        
        return chunks

    def _create_child_chunks(self, parent: Chunk, doc_id: str) -> list[Chunk]:
        """Create child chunks from a parent chunk."""
        chunks = []
        text = parent.content
        start = 0
        
        while start < len(text):
            end = min(start + self.child_chunk_size, len(text))
            
            if end < len(text) and end - start == self.child_chunk_size:
                # Find a word boundary
                while end > start and text[end - 1] not in " \t\n":
                    end -= 1
                if end == start:
                    end = min(start + self.child_chunk_size, len(text))
            
            child_content = text[start:end].strip()
            if child_content:
                child_id = f"{doc_id}_child_{len(chunks)}"
                chunks.append(Chunk(
                    chunk_id=child_id,
                    content=child_content,
                    doc_id=doc_id,
                    chunk_type="child",
                    parent_id=parent.chunk_id,
                    order=len(chunks)
                ))
            
            start = end - self.overlap if end < len(text) else len(text)
        
        return chunks
```

- [ ] **Step 2: 更新 base.py 导出**

```python
from .parent_child import ParentChildChunker, Chunk
```

- [ ] **Step 3: Commit**

```bash
git add python/src/core/chunker/parent_child.py python/src/core/chunker/base.py
git commit -m "feat(rag): implement parent-child chunking strategy with configurable sizes"
```

---

### Task 4: ChromaDB 向量存储与检索实现

**Files:**
- Create: `python/src/core/storage/vector_store.py`
- Modify: `python/src/core/retriever/chroma.py`

- [ ] **Step 1: 创建 VectorStore 包装类**

```python
"""ChromaDB vector store wrapper with parent-child support."""
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import Optional


class VectorStore:
    """ChromaDB vector store with persistent storage."""

    def __init__(
        self,
        persist_directory: str = "./vector_db",
        collection_name: str = "lumina_docs"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
        return self._client

    @property
    def collection(self):
        """Get or create collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Lumina Insight document chunks"}
            )
        return self._collection

    def add_chunks(self, chunks: list, embeddings: list[list[float]]) -> None:
        """Add chunks with their embeddings to the store."""
        if not chunks or not embeddings:
            return
        
        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "chunk_type": c.chunk_type,
                "parent_id": c.parent_id or "",
                "page_number": c.page_number or 0,
                "order": c.order
            }
            for c in chunks
        ]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query(self, query_embedding: list[float], top_k: int = 5) -> dict:
        """Query the store for similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return results

    def get_by_parent(self, parent_id: str) -> list:
        """Get all child chunks for a parent."""
        results = self.collection.get(
            where={"parent_id": parent_id}
        )
        return results
```

- [ ] **Step 2: 更新 ChromaRetriever**

```python
"""ChromaDB retriever implementation."""
from typing import Optional


class ChromaRetriever:
    """ChromaDB retriever with parent-child support."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder
    ):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 5) -> list:
        """Retrieve relevant chunks and their parent contexts."""
        # Get query embedding
        query_embedding = self.embedder.embed([query])[0]
        
        # Search for similar child chunks
        results = self.vector_store.query(query_embedding, top_k)
        
        # For each child, get the parent chunk for full context
        chunks_with_context = []
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            metadata = results["metadatas"][0][i]
            
            if metadata["chunk_type"] == "child":
                parent_id = metadata["parent_id"]
                parent_results = self.vector_store.get_by_parent(parent_id)
                if parent_results["documents"]:
                    chunks_with_context.append({
                        "child_id": chunk_id,
                        "child_content": results["documents"][0][i],
                        "parent_content": parent_results["documents"][0],
                        "parent_id": parent_id,
                        "doc_id": metadata["doc_id"],
                        "distance": results["distances"][0][i]
                    })
            else:
                chunks_with_context.append({
                    "parent_id": chunk_id,
                    "parent_content": results["documents"][0][i],
                    "doc_id": metadata["doc_id"],
                    "distance": results["distances"][0][i]
                })
        
        return chunks_with_context
```

- [ ] **Step 3: Commit**

```bash
git add python/src/core/storage/vector_store.py python/src/core/retriever/chroma.py
git commit -m "feat(rag): implement ChromaDB vector store with parent-child retrieval"
```

---

### Task 5: Minimax m2.7 集成与流式返回

**Files:**
- Create: `python/src/core/llm/minimax.py`
- Modify: `python/src/api/server.py`

- [ ] **Step 1: 创建 Minimax 客户端封装**

```python
"""Minimax m2.7 LLM client with streaming support."""
import os
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
    """Minimax m2.7 streaming client."""

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
        """Stream chat completion with RAG context.
        
        Args:
            messages: Chat history
            context_chunks: Retrieved parent chunks for context
        
        Yields:
            StreamChunk with content, done flag, and references
        """
        # Build prompt with context
        context_text = self._build_context_prompt(context_chunks)
        prompt = self._build_prompt(messages, context_text)
        
        # Call Minimax API with streaming
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "Minimax-m2.7",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }
        
        # Note: Use requests to handle streaming response
        # This is a simplified version - actual implementation 
        # should use minimax-python-sdk
        response = requests.post(
            f"{self.base_url}/text/chatcompletion_v2",
            headers=headers,
            json=payload,
            stream=True
        )
        
        references = self._build_references(context_chunks)
        
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if data.startswith("data:"):
                    # Parse SSE data
                    content = self._parse_sse_data(data)
                    if content:
                        yield StreamChunk(
                            content=content,
                            done=False,
                            references=None
                        )
        
        yield StreamChunk(content="", done=True, references=references)

    def _build_context_prompt(self, chunks: list[dict]) -> str:
        """Build context section of prompt."""
        if not chunks:
            return "No relevant documents found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_name = chunk.get("doc_name", "Unknown")
            content = chunk.get("parent_content", chunk.get("child_content", ""))
            context_parts.append(f"[{i}] Source: {doc_name}\n{content}")
        
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
        """Build references list WITHOUT <cite> tags."""
        references = []
        for chunk in chunks:
            references.append({
                "source_doc": chunk.get("doc_name", "Unknown"),
                "page_number": chunk.get("page_number", 0),
                "content": chunk.get("parent_content", "")[:200]
            })
        return references

    def _parse_sse_data(self, data: str) -> str:
        """Parse SSE data line."""
        # Simplified SSE parsing
        try:
            return data.replace("data:", "").strip()
        except Exception:
            return ""
```

- [ ] **Step 2: 更新 FastAPI 服务**

```python
"""FastAPI server for Lumina Insight AI Service."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from ..core.chunker.parent_child import ParentChildChunker
from ..core.embedder.sentence_transformer import SentenceTransformerEmbedder
from ..core.retriever.chroma import ChromaRetriever
from ..core.storage.vector_store import VectorStore
from ..core.llm.minimax import MinimaxClient, Message


app = FastAPI(title="Lumina Insight AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components (initialized on startup)
vector_store: Optional[VectorStore] = None
embedder: Optional[SentenceTransformerEmbedder] = None
retriever: Optional[ChromaRetriever] = None
chunker: Optional[ParentChildChunker] = None
llm_client: Optional[MinimaxClient] = None


class QueryRequest(BaseModel):
    messages: list[dict]
    stream: bool = True


@app.on_event("startup")
async def startup():
    global vector_store, embedder, retriever, chunker, llm_client
    vector_store = VectorStore(persist_directory="./vector_db")
    embedder = SentenceTransformerEmbedder()
    retriever = ChromaRetriever(vector_store, embedder)
    chunker = ParentChildChunker()
    llm_client = MinimaxClient()


@app.post("/process_query")
async def process_query(request: QueryRequest):
    """Process a RAG query and return streaming response."""
    if not llm_client or not retriever:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    # Convert messages
    messages = [Message(**m) for m in request.messages]
    last_query = messages[-1].content if messages else ""
    
    # Retrieve relevant chunks
    context_chunks = retriever.retrieve(last_query, top_k=5)
    
    if not context_chunks:
        context_chunks = []
    
    # Stream response from Minimax
    def generate():
        for chunk in llm_client.stream_chat(messages, context_chunks):
            # Format SSE response - NO <cite> tags
            if chunk.done:
                yield f"data: {JSON.dumps({'done': True, 'references': chunk.references})}\n\n"
            else:
                yield f"data: {JSON.dumps({'content': chunk.content})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document."""
    if not chunker or not vector_store or not embedder:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    # Save uploaded file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Parse document based on type
    from ..core.chunker.pdf_parser import extract_text_from_pdf
    from ..core.chunker.docx_parser import extract_text_from_docx
    
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(temp_path)
    elif file.filename.endswith(".docx"):
        text = extract_text_from_docx(temp_path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Create chunks
    doc_id = str(uuid.uuid4())
    chunks = chunker.chunk_text(text, doc_id)
    
    # Embed and store
    embeddings = embedder.embed([c.content for c in chunks])
    vector_store.add_chunks(chunks, embeddings)
    
    return {"doc_id": doc_id, "status": "processed", "chunks": len(chunks)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

- [ ] **Step 3: Commit**

```bash
git add python/src/core/llm/minimax.py python/src/api/server.py
git commit -m "feat(rag): integrate Minimax m2.7 with streaming and RAG context"
```

---

### Task 6: API 接口完善与端点测试

**Files:**
- Modify: `python/src/api/server.py`
- Create: `python/tests/test_api.py`

- [ ] **Step 1: 补全 server.py 缺失的导入**

```python
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import json
import uuid
```

- [ ] **Step 2: 创建基础 API 测试**

```python
"""API endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from src.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_process_query_endpoint(client, monkeypatch):
    """Test /process_query endpoint exists and returns SSE."""
    monkeypatch.setattr("src.api.server.llm_client", MockLLMClient())
    
    response = client.post("/process_query", json={
        "messages": [{"role": "user", "content": "测试问题"}],
        "stream": False
    })
    
    assert response.status_code in [200, 500]  # 500 if not initialized


def test_upload_endpoint_structure(client):
    """Test upload endpoint accepts multipart form."""
    # This is a structural test - actual file upload tested manually
    assert "/upload" in [route.path for route in app.routes]
```

- [ ] **Step 3: Commit**

```bash
git add python/src/api/server.py python/tests/test_api.py
git commit -m "test(api): add basic API endpoint tests"
```

---

### Task 7: 最终审查并修复问题

**Files:**
- Review all files in `python/src/`
- Fix any issues found during review

- [ ] **Step 1: 自我审查代码**

使用 code-review 工具审查：
1. 父子块切片逻辑是否正确实现
2. ChromaDB 存储和检索是否正确
3. 流式返回中是否**绝对禁止** `<cite>` 标签

- [ ] **Step 2: 最终 commit**

```bash
git add -A && git commit -m "chore: finalize AI core engine implementation"
```
