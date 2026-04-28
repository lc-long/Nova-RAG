"""FastAPI server for Lumina Insight AI Service."""
import os
import json
import uuid
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

from fastapi import FastAPI, HTTPException, UploadFile, File
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
            if chunk.done:
                yield f"data: {json.dumps({'done': True, 'references': chunk.references})}\n\n"
            else:
                yield f"data: {json.dumps({'content': chunk.content})}\n\n"

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
async def ingest_document(req: IngestRequest):
    """Ingest a document from a file path (called by Go backend)."""
    if not chunker or not vector_store or not embedder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    file_path = req.file_path
    print(f"[Ingest] Received: doc_id={req.doc_id} filename={req.filename} file_path={file_path}")

    if not os.path.exists(file_path):
        print(f"[Ingest] ERROR: file not found at {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        if req.filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif req.filename.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    doc_id = req.doc_id
    chunks = chunker.chunk(text, doc_id)
    embeddings = embedder.embed([c.content for c in chunks])
    vector_store.add_chunks(chunks, embeddings)

    return {"doc_id": doc_id, "status": "processed", "chunks": len(chunks)}


@app.post("/reset_db")
async def reset_db():
    """Clear all documents from ChromaDB (for testing)."""
    global vector_store
    if not vector_store:
        raise HTTPException(status_code=500, detail="Service not initialized")
    try:
        vector_store.collection.delete(where={})
        print("[ResetDB] All documents deleted from ChromaDB")
        return {"status": "ok", "message": "All documents cleared"}
    except Exception as e:
        print(f"[ResetDB] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("[Lumina Insight] Starting server on http://0.0.0.0:5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)