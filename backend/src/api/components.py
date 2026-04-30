"""Global shared components initialized at startup."""
from typing import Optional

from ..core.storage.vector_store import VectorStore
from ..core.embedder.sentence_transformer import SentenceTransformerEmbedder
from ..core.retriever.hybrid_search import HybridRetriever
from ..core.retriever.bm25_index import BM25Indexer
from ..core.chunker.parent_child import ParentChildChunker
from ..core.llm.minimax import MinimaxClient

vector_store: Optional[VectorStore] = None
embedder: Optional[SentenceTransformerEmbedder] = None
bm25_indexer: Optional[BM25Indexer] = None
retriever: Optional[HybridRetriever] = None
chunker: Optional[ParentChildChunker] = None
llm_client: Optional[MinimaxClient] = None


def init_components():
    """Initialize all shared components. Called once at startup."""
    global vector_store, embedder, retriever, chunker, llm_client, bm25_indexer
    print("[Nova-RAG] Initializing components...")
    vector_store = VectorStore(persist_directory="./vector_db")
    embedder = SentenceTransformerEmbedder()
    bm25_indexer = BM25Indexer(persist_directory="./vector_db")
    retriever = HybridRetriever(vector_store, embedder, bm25_indexer)
    chunker = ParentChildChunker()
    llm_client = MinimaxClient()
    print("[Nova-RAG] All components ready!")