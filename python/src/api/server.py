"""FastAPI server for Lumina Insight AI Service."""
import os
import json
import uuid
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from ..core.chunker.parent_child import ParentChildChunker
from ..core.chunker.pdf_parser import extract_text_from_pdf
from ..core.chunker.docx_parser import extract_text_from_docx
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

vector_store: Optional[VectorStore] = None
embedder: Optional[SentenceTransformerEmbedder] = None
retriever: Optional[ChromaRetriever] = None
chunker: Optional[ParentChildChunker] = None
llm_client: Optional[MinimaxClient] = None

# In-memory task store for async ingestion tracking
# task_id -> {"status": "processing"|"completed"|"failed", "result": ..., "error": ...}
task_store: dict = {}


class QueryRequest(BaseModel):
    messages: list[dict]
    stream: bool = True


@app.on_event("startup")
async def startup():
    global vector_store, embedder, retriever, chunker, llm_client
    print("[Lumina Insight] Initializing components...")
    vector_store = VectorStore(persist_directory="./vector_db")
    embedder = SentenceTransformerEmbedder()
    retriever = ChromaRetriever(vector_store, embedder)
    chunker = ParentChildChunker()
    llm_client = MinimaxClient()
    print("[Lumina Insight] All components ready!")


@app.post("/process_query")
async def process_query(request: QueryRequest):
    if not llm_client or not retriever:
        raise HTTPException(status_code=500, detail="Service not initialized")

    messages = [Message(**m) for m in request.messages]
    last_query = messages[-1].content if messages else ""

    context_chunks = retriever.retrieve(last_query, top_k=5)
    if not context_chunks:
        context_chunks = []

    def generate():
        for chunk in llm_client.stream_chat(messages, context_chunks):
            if chunk.chunk_type == "done":
                yield f"data: {json.dumps({'done': True, 'references': chunk.references})}\n\n"
            elif chunk.chunk_type == "reasoning":
                yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.content})}\n\n"
            elif chunk.chunk_type == "answer":
                yield f"data: {json.dumps({'type': 'answer', 'content': chunk.content})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not chunker or not vector_store or not embedder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        if file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(temp_path)
        elif file.filename.endswith(".docx"):
            text = extract_text_from_docx(temp_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    doc_id = str(uuid.uuid4())
    chunks = chunker.chunk(text, doc_id)
    embeddings = embedder.embed([c.content for c in chunks])
    vector_store.add_chunks(chunks, embeddings)

    return {"doc_id": doc_id, "status": "processed", "chunks": len(chunks)}


class IngestRequest(BaseModel):
    doc_id: str
    filename: str
    file_path: str


@app.post("/ingest")
async def ingest_document(req: IngestRequest, background_tasks: BackgroundTasks):
    """Ingest a document asynchronously. Returns immediately with a task_id.

    Go backend should poll GET /task_status/{task_id} for completion.
    """
    if not chunker or not vector_store or not embedder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    task_id = str(uuid.uuid4())
    file_path = req.file_path

    print(f"[Ingest] Queued: doc_id={req.doc_id} task_id={task_id} filename={req.filename}")

    # Register task as processing
    task_store[task_id] = {
        "status": "processing",
        "doc_id": req.doc_id,
        "filename": req.filename,
        "result": None,
        "error": None,
        "chunks": 0,
    }

    # Schedule actual ingestion in background
    background_tasks.add_task(run_ingestion, task_id, req.doc_id, req.filename, file_path)

    return {"task_id": task_id, "status": "processing"}


def run_ingestion(task_id: str, doc_id: str, filename: str, file_path: str):
    """Background task that performs the actual document ingestion."""
    global chunker, vector_store, embedder

    print(f"[Ingest][{task_id}] Starting ingestion for {filename}")

    result = {"text": None, "error": None}

    if filename.endswith(".pdf"):
        import subprocess

        PYTHON_EXE = r"D:\code\ai\rag\python\.venv\Scripts\python.exe"

        # Use subprocess with timeout to prevent pdfplumber from hanging
        # on complex PDFs (calls C extension that can't be interrupted by threads)
        parse_script = f"""
import sys
sys.path.insert(0, r'D:\\code\\ai\\rag\\python\\src')
from core.chunker.pdf_parser import extract_text_from_pdf
print(extract_text_from_pdf({repr(file_path)}))
"""
        try:
            proc = subprocess.run(
                [PYTHON_EXE, "-c", parse_script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode == 0:
                result["text"] = proc.stdout
            else:
                result["error"] = proc.stderr[:500] if proc.stderr else "Unknown parse error"
        except subprocess.TimeoutExpired:
            result["error"] = f"Timeout: parsing exceeded 120s for {filename}"
    elif filename.endswith(".docx"):
        try:
            result["text"] = extract_text_from_docx(file_path)
        except Exception as e:
            result["error"] = str(e)
    elif filename.endswith(".txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                result["text"] = f.read()
        except Exception as e:
            result["error"] = str(e)
    else:
        result["error"] = f"Unsupported file type: {filename}"

    if result["error"]:
        print(f"[Ingest][{task_id}] Failed: {result['error']}")
        task_store[task_id]["status"] = "failed"
        task_store[task_id]["error"] = result["error"]
        return

    text = result["text"]
    print(f"[Ingest][{task_id}] Parsed {len(text)} chars from {filename}")

    try:
        chunks = chunker.chunk(text, doc_id)
        prefix = f"[来源文件：{filename}]\n"
        for chunk in chunks:
            chunk.content = prefix + chunk.content

        embeddings = embedder.embed([c.content for c in chunks])
        vector_store.add_chunks(chunks, embeddings, source=filename)

        print(f"[Ingest][{task_id}] Completed: {len(chunks)} chunks stored")

        task_store[task_id]["status"] = "completed"
        task_store[task_id]["result"] = "processed"
        task_store[task_id]["chunks"] = len(chunks)

    except Exception as e:
        print(f"[Ingest][{task_id}] Failed: {e}")
        task_store[task_id]["status"] = "failed"
        task_store[task_id]["error"] = str(e)


@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """Return the status of an async ingestion task."""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    task = task_store[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "doc_id": task.get("doc_id"),
        "filename": task.get("filename"),
        "result": task.get("result"),
        "error": task.get("error"),
        "chunks": task.get("chunks", 0),
    }


@app.post("/reset_db")
async def reset_db():
    """Clear all documents from ChromaDB (for testing)."""
    global vector_store
    if not vector_store:
        raise HTTPException(status_code=500, detail="Service not initialized")
    try:
        try:
            vector_store.client.delete_collection(name=vector_store.collection_name)
            print("[ResetDB] Collection deleted")
        except Exception as col_err:
            print(f"[ResetDB] Collection delete skipped (may not exist): {col_err}")
        vector_store._collection = None
        print("[ResetDB] Collection reference reset (will auto-recreate on next access)")
        return {"status": "ok", "message": "ChromaDB reset complete"}
    except Exception as e:
        print(f"[ResetDB] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("[Lumina Insight] Starting server on http://0.0.0.0:5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
