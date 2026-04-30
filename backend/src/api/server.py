"""FastAPI server for Nova-RAG - Unified Python Backend."""
import warnings

# Suppress pkg_resources deprecation warning from legacy dependencies like jieba
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API")

import os

from dotenv import load_dotenv
load_dotenv()

os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .components import init_components
from .database import Base, engine
from .routes import docs, chat

app = FastAPI(title="Nova-RAG Unified Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    init_components()


app.include_router(docs.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


if __name__ == "__main__":
    print("[Nova-RAG] Starting server on http://0.0.0.0:5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)