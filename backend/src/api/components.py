"""Global shared components initialized at startup."""
import logging
from dataclasses import dataclass

logger = logging.getLogger("nova_rag")

from ..core.storage.vector_store import VectorStore
from ..core.embedder.aliyun_embedder import AliyunEmbedder
from ..core.retriever.hybrid_search import HybridRetriever
from ..core.retriever.bm25_index import BM25Indexer
from ..core.chunker.parent_child import ParentChildChunker
from ..core.llm.minimax import MinimaxClient


@dataclass
class Components:
    vector_store: VectorStore
    embedder: AliyunEmbedder
    bm25_indexer: BM25Indexer
    retriever: HybridRetriever
    chunker: ParentChildChunker
    llm_client: MinimaxClient


def create_components() -> Components:
    """Initialize and return all shared components. Called once at startup."""
    logger.info("[Nova-RAG] Initializing components...")
    vector_store = VectorStore()
    embedder = AliyunEmbedder()
    bm25_indexer = BM25Indexer(persist_directory="./vector_db")
    retriever = HybridRetriever(vector_store, embedder, bm25_indexer)
    chunker = ParentChildChunker()
    llm_client = MinimaxClient()
    logger.info("[Nova-RAG] All components ready!")
    return Components(
        vector_store=vector_store,
        embedder=embedder,
        bm25_indexer=bm25_indexer,
        retriever=retriever,
        chunker=chunker,
        llm_client=llm_client,
    )