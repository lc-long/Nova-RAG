"""Global shared components initialized at startup."""
from dataclasses import dataclass
from typing import Optional

from ..core.storage.vector_store import VectorStore
from ..core.embedder.sentence_transformer import SentenceTransformerEmbedder
from ..core.retriever.hybrid_search import HybridRetriever
from ..core.retriever.bm25_index import BM25Indexer
from ..core.chunker.parent_child import ParentChildChunker
from ..core.llm.minimax import MinimaxClient


@dataclass
class Components:
    vector_store: VectorStore
    embedder: SentenceTransformerEmbedder
    bm25_indexer: BM25Indexer
    retriever: HybridRetriever
    chunker: ParentChildChunker
    llm_client: MinimaxClient


def create_components() -> Components:
    """Initialize and return all shared components. Called once at startup."""
    print("[Nova-RAG] Initializing components...")
    vector_store = VectorStore(persist_directory="./vector_db")
    embedder = SentenceTransformerEmbedder()
    bm25_indexer = BM25Indexer(persist_directory="./vector_db")
    retriever = HybridRetriever(vector_store, embedder, bm25_indexer)
    chunker = ParentChildChunker()
    llm_client = MinimaxClient()
    print("[Nova-RAG] All components ready!")
    return Components(
        vector_store=vector_store,
        embedder=embedder,
        bm25_indexer=bm25_indexer,
        retriever=retriever,
        chunker=chunker,
        llm_client=llm_client,
    )