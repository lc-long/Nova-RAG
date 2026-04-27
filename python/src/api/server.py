"""FastAPI server for Lumina Insight AI Service - DIAGNOSTIC VERSION."""
import os
import sys
import json
import uuid
import traceback
from typing import Optional

print("[DEBUG] Starting server.py...")

try:
    print("[DEBUG] Importing dotenv...")
    from dotenv import load_dotenv
    print("[DEBUG] dotenv imported successfully")

    print("[DEBUG] Loading .env file...")
    load_dotenv()

    # Configure HuggingFace mirror for Chinese network environment
    os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
    print(f"[DEBUG] HF_ENDPOINT set to: {os.environ['HF_ENDPOINT']}")

    print(f"[DEBUG] MINIMAX_API_KEY loaded: {bool(os.getenv('MINIMAX_API_KEY'))}")
    print(f"[DEBUG] MINIMAX_GROUP_ID loaded: {bool(os.getenv('MINIMAX_GROUP_ID'))}")

    print("[DEBUG] Importing FastAPI and dependencies...")
    from fastapi import FastAPI, HTTPException, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    print("[DEBUG] FastAPI imports successful")

    print("[DEBUG] Importing uvicorn...")
    import uvicorn
    print("[DEBUG] uvicorn imported successfully")

    print("[DEBUG] Importing ChromaDB...")
    import chromadb
    from chromadb.config import Settings
    print("[DEBUG] ChromaDB imported successfully")

    print("[DEBUG] Importing sentence_transformers...")
    from sentence_transformers import SentenceTransformer
    print("[DEBUG] sentence_transformers imported successfully")

    print("[DEBUG] Importing LangChain text splitter...")
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print("[DEBUG] LangChain imports successful")

    print("[DEBUG] Importing project modules...")
    from ..core.chunker.parent_child import ParentChildChunker
    print("[DEBUG] ParentChildChunker imported")
    from ..core.chunker.pdf_parser import extract_text_from_pdf
    print("[DEBUG] pdf_parser imported")
    from ..core.chunker.docx_parser import extract_text_from_docx
    print("[DEBUG] docx_parser imported")
    from ..core.embedder.sentence_transformer import SentenceTransformerEmbedder
    print("[DEBUG] SentenceTransformerEmbedder imported")
    from ..core.retriever.chroma import ChromaRetriever
    print("[DEBUG] ChromaRetriever imported")
    from ..core.storage.vector_store import VectorStore
    print("[DEBUG] VectorStore imported")
    from ..core.llm.minimax import MinimaxClient, Message
    print("[DEBUG] MinimaxClient imported")

    print("[DEBUG] All imports completed successfully!")

except Exception as e:
    print(f"[ERROR] Exception during import/setup: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[DEBUG] Creating FastAPI app...")
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
    print("[Lumina Insight AI Service] Initializing components...")
    try:
        vector_store = VectorStore(persist_directory="./vector_db")
        print("[DEBUG] VectorStore initialized")
        embedder = SentenceTransformerEmbedder()
        print("[DEBUG] Embedder initialized")
        retriever = ChromaRetriever(vector_store, embedder)
        print("[DEBUG] Retriever initialized")
        chunker = ParentChildChunker()
        print("[DEBUG] Chunker initialized")
        llm_client = MinimaxClient()
        print("[DEBUG] LLM client initialized")
        print("[Lumina Insight AI Service] All components initialized successfully!")
    except Exception as e:
        print(f"[ERROR] Exception during startup: {e}")
        traceback.print_exc()


@app.post("/process_query")
async def process_query(request: QueryRequest):
    """Process a RAG query and return streaming response."""
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
    """Upload and process a document."""
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


if __name__ == "__main__":
    print("[Lumina Insight AI Service] Starting server on http://0.0.0.0:5000")
    try:
        uvicorn.run(app, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"[ERROR] Exception during uvicorn.run: {e}")
        traceback.print_exc()