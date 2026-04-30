"""ChromaDB retriever implementation with parent-child support."""
import re
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
        """Retrieve relevant chunks with fallback for summarization queries.

        If query contains .pdf/.docx filename hints, tries metadata search first.
        Falls back to relaxed threshold if vector search returns nothing.
        """
        # Check if query mentions a specific filename
        file_match = re.search(r'([^\s/\\]+\.(?:pdf|docx))', query, re.IGNORECASE)

        if file_match:
            filename_hint = file_match.group(1).lower()
            results = self._metadata_search(filename_hint, top_k)
            if results:
                return results

        # Standard vector search
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

        # Fallback: if nothing found, return top_k without distance filter
        if not chunks_with_context:
            results_relaxed = self.vector_store.query(query_embedding, top_k)
            for i in range(len(results_relaxed["ids"][0])):
                metadata = results_relaxed["metadatas"][0][i]
                distance = results_relaxed["distances"][0][i]
                text = results_relaxed["documents"][0][i]
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
                            "child_id": results_relaxed["ids"][0][i],
                            "child_content": text,
                            "parent_content": parent_results["documents"][0],
                            "parent_id": parent_id,
                            "doc_id": metadata["doc_id"],
                            "page_number": metadata.get("page_number", 0),
                            "distance": distance
                        })
                else:
                    chunks_with_context.append({
                        "parent_id": results_relaxed["ids"][0][i],
                        "parent_content": text,
                        "doc_id": metadata["doc_id"],
                        "page_number": metadata.get("page_number", 0),
                        "distance": distance
                    })

        return chunks_with_context

    def _metadata_search(self, filename_hint: str, top_k: int) -> list[dict]:
        """Search by source metadata containing filename hint."""
        try:
            all_data = self.vector_store.collection.get(
                where={"source": {"$contains": filename_hint}},
                include=["documents", "metadatas", "distances"]
            )
            results = []
            seen_parent_ids = set()
            for i in range(len(all_data["ids"])):
                metadata = all_data["metadatas"][i]
                if metadata["chunk_type"] == "child":
                    parent_id = metadata["parent_id"]
                    if parent_id in seen_parent_ids:
                        continue
                    seen_parent_ids.add(parent_id)
                    parent_results = self.vector_store.get_by_parent(parent_id)
                    if parent_results["documents"]:
                        results.append({
                            "child_id": all_data["ids"][i],
                            "child_content": all_data["documents"][i],
                            "parent_content": parent_results["documents"][0],
                            "parent_id": parent_id,
                            "doc_id": metadata["doc_id"],
                            "page_number": metadata.get("page_number", 0),
                            "distance": 0.0
                        })
                else:
                    results.append({
                        "parent_id": all_data["ids"][i],
                        "parent_content": all_data["documents"][i],
                        "doc_id": metadata["doc_id"],
                        "page_number": metadata.get("page_number", 0),
                        "distance": 0.0
                    })
            return results[:top_k]
        except Exception:
            return []