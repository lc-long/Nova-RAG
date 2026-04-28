"""ChromaDB vector store wrapper with parent-child support."""
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
            import chromadb
            from chromadb.config import Settings
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

    def add_chunks(self, chunks: list, embeddings: list[list[float]], source: str = "") -> None:
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
                "order": c.order,
                "source": source,
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
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def get_by_parent(self, parent_id: str) -> dict:
        """Get all child chunks for a parent."""
        results = self.collection.get(
            where={"parent_id": parent_id}
        )
        return results
