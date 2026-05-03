"""Centralized RAG configuration with env overrides.

All tunable parameters live here. Override via environment variables (backend/.env).
"""
import os

# --- Chunker ---
CHUNK_PARENT_SIZE = int(os.getenv("CHUNK_PARENT_SIZE", "2000"))
CHUNK_CHILD_SIZE = int(os.getenv("CHUNK_CHILD_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# --- Embedder ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-v3")
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "6"))
EMBED_BATCH_SLEEP = float(os.getenv("EMBED_BATCH_SLEEP", "0.1"))
EMBED_MAX_TEXT_CHARS = int(os.getenv("EMBED_MAX_TEXT_CHARS", "6000"))

# --- Retriever ---
RECALL_MULTIPLIER = int(os.getenv("RECALL_MULTIPLIER", "15"))
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "6"))
RRF_K = int(os.getenv("RRF_K", "30"))
MISSING_RANK = int(os.getenv("MISSING_RANK", "1000"))
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "10.0"))

# --- Reranker ---
RERANK_MODEL = os.getenv("RERANK_MODEL", "gte-rerank")
RERANK_MIN_SCORE = float(os.getenv("RERANK_MIN_SCORE", "0.5"))

# --- Chat ---
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "6000"))
MAX_HISTORY_TOKENS = int(os.getenv("MAX_HISTORY_TOKENS", "2000"))

# --- Query Rewriter ---
SHORT_QUERY_THRESHOLD = int(os.getenv("SHORT_QUERY_THRESHOLD", "10"))

# --- Query expansion patterns (JSON file path, optional) ---
QUERY_PATTERNS_FILE = os.getenv("QUERY_PATTERNS_FILE", "")

# --- Image Storage ---
IMAGE_STORAGE_DIR = os.getenv("IMAGE_STORAGE_DIR", "uploads/images")

# --- OCR ---
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "15"))
OCR_FULL_DOCUMENT = os.getenv("OCR_FULL_DOCUMENT", "false").lower() == "true"
