"""FastAPI server for Nova-RAG - Unified Python Backend."""
import warnings

# Suppress pkg_resources deprecation warning from legacy dependencies like jieba
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API")

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .components import create_components
from .database import Base, engine
from ..core.storage.vector_store import init_pgvector
from .routes import docs, chat, conversations

logger = logging.getLogger("nova_rag")

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Nova-RAG starting up...")
    init_pgvector()
    Base.metadata.create_all(bind=engine)
    app.state.components = create_components()
    logger.info("Nova-RAG components initialized.")
    yield
    logger.info("Nova-RAG shutting down.")


app = FastAPI(title="Nova-RAG Unified Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok", "service": "Nova-RAG"}


app.include_router(docs.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")


if __name__ == "__main__":
    logger.info("Starting server on http://0.0.0.0:5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
