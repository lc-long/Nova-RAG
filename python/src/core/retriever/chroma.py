"""ChromaDB retriever implementation with parent-child support."""
from typing import Optional


class ChromaRetriever:
    """ChromaDB retriever with parent-child support and deduplication."""

    def __init__(
        self,
        vector_store,
        embedder,
        distance_threshold: float = 10.0
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.distance_threshold = distance_threshold

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve relevant chunks and their parent contexts.

        Applies distance threshold to filter out irrelevant results,
        then deduplicates by parent_id and text content.
        """
        query_embedding = self.embedder.embed([query])[0]
        results = self.vector_store.query(query_embedding, top_k)

        chunks_with_context = []
        seen_parent_ids = set()
        seen_texts = set()

        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            if distance > self.distance_threshold:
                continue

            text = results["documents"][0][i]
            norm_text = text.replace("\n", " ").strip()
            if norm_text in seen_texts:
                continue
            seen_texts.add(norm_text)

            if metadata["chunk_type"] == "child":
                parent_id = metadata["parent_id"]
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)

                parent_results = self.vector_store.get_by_parent(parent_id)
                if parent_results["documents"]:
                    chunks_with_context.append({
                        "child_id": chunk_id,
                        "child_content": text,
                        "parent_content": parent_results["documents"][0],
                        "parent_id": parent_id,
                        "doc_id": metadata["doc_id"],
                        "page_number": metadata.get("page_number", 0),
                        "distance": distance
                    })
            else:
                chunks_with_context.append({
                    "parent_id": chunk_id,
                    "parent_content": text,
                    "doc_id": metadata["doc_id"],
                    "page_number": metadata.get("page_number", 0),
                    "distance": distance
                })

        return chunks_with_context