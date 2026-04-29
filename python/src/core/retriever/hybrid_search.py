"""Hybrid retriever combining dense (ChromaDB) and sparse (BM25) search.

Uses Reciprocal Rank Fusion (RRF) to merge results from both engines.
"""
import re
from typing import Optional

from .bm25_index import BM25Indexer


class HybridRetriever:
    """Hybrid retriever using vector + BM25 with RRF fusion."""

    def __init__(
        self,
        vector_store,
        embedder,
        bm25_indexer: Optional[BM25Indexer] = None,
        distance_threshold: float = 10.0,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.bm25_indexer = bm25_indexer
        self.distance_threshold = distance_threshold
        self.rrf_k = rrf_k

    def _build_result_map(
        self,
        results: list[dict],
        rank_offset: int = 0
    ) -> dict[str, tuple[int, dict]]:
        """Build {chunk_id: (rank, result_dict)} map for RRF."""
        result_map = {}
        for i, r in enumerate(results):
            key = r.get("child_id") or r.get("parent_id")
            if key:
                result_map[key] = (rank_offset + i, r)
        return result_map

    def _deduplicate_and_enrich(
        self,
        result_map: dict[str, tuple[int, dict]]
    ) -> list[dict]:
        """Apply parent-child deduplication and return ordered list."""
        seen_parent_ids = set()
        seen_texts = set()
        ordered = sorted(result_map.items(), key=lambda x: x[1][0])
        chunks = []

        for chunk_id, (rank, r) in ordered:
            text = r.get("child_content") or r.get("parent_content", "")
            norm_text = text.replace("\n", " ").strip()
            if norm_text in seen_texts:
                continue
            seen_texts.add(norm_text)

            parent_id = r.get("parent_id")
            if r.get("child_id") and parent_id:
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)
                chunks.append(r)
            else:
                chunks.append(r)

        return chunks

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Hybrid search: vector + BM25 with RRF fusion."""
        # --- Vector (dense) retrieval ---
        file_match = re.search(r'([^\s/\\]+\.(?:pdf|docx))', query, re.IGNORECASE)

        if file_match:
            filename_hint = file_match.group(1).lower()
            dense_results = self._metadata_search(filename_hint, top_k * 2)
        else:
            query_embedding = self.embedder.embed([query])[0]
            dense_results = self._vector_search(query_embedding, top_k * 2)

        # --- BM25 (sparse) retrieval ---
        sparse_results = []
        if self.bm25_indexer:
            sparse_ids = self.bm25_indexer.search(query, top_k=top_k * 2)
            for chunk_id, bm25_score in sparse_ids:
                content = self.bm25_indexer.chunk_id_to_content.get(chunk_id, "")
                doc_id = self.bm25_indexer.chunk_id_to_doc.get(chunk_id, "")
                parent_id = ""
                # Get parent_id from vector store if needed
                try:
                    vec_result = self.vector_store.collection.get(ids=[chunk_id])
                    if vec_result["metadatas"]:
                        parent_id = vec_result["metadatas"][0].get("parent_id", "")
                except Exception:
                    pass
                sparse_results.append({
                    "child_id": None,
                    "parent_id": chunk_id,
                    "child_content": "",
                    "parent_content": content,
                    "doc_id": doc_id,
                    "page_number": 0,
                    "distance": bm25_score,
                })

        # --- RRF Fusion ---
        fused = self._rrf_fuse(dense_results, sparse_results, top_k)
        return fused

    def _rrf_fuse(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
        top_k: int
    ) -> list[dict]:
        """Reciprocal Rank Fusion of two result lists."""
        rrf_scores: dict[str, float] = {}

        for rank, result in enumerate(dense_results):
            key = result.get("child_id") or result.get("parent_id")
            if key:
                # Normalize distance to a relevance-like score (lower distance = higher relevance)
                distance = result.get("distance", 0)
                vec_score = 1.0 / (self.rrf_k + distance)
                rrf_scores[key] = rrf_scores.get(key, 0) + vec_score

        for rank, result in enumerate(sparse_results):
            key = result.get("child_id") or result.get("parent_id")
            if key:
                # BM25 score is already a relevance score (higher = better)
                bm25_score = result.get("distance", 0)
                sparse_normalized = bm25_score / 10.0  # normalize to similar range
                rrf_scores[key] = rrf_scores.get(key, 0) + sparse_normalized

        # Build result map with all metadata
        all_results = {}
        for r in dense_results:
            key = r.get("child_id") or r.get("parent_id")
            if key:
                all_results[key] = r
        for r in sparse_results:
            key = r.get("child_id") or r.get("parent_id")
            if key:
                if key not in all_results:
                    all_results[key] = r

        # Sort by RRF score
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

        chunks = []
        seen_parent_ids = set()
        seen_texts = set()

        for key in sorted_keys:
            if len(chunks) >= top_k:
                break
            r = all_results[key]
            text = r.get("child_content") or r.get("parent_content", "")
            norm_text = text.replace("\n", " ").strip()
            if norm_text in seen_texts:
                continue
            seen_texts.add(norm_text)

            parent_id = r.get("parent_id")
            if r.get("child_id") and parent_id:
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)
                chunks.append(r)
            else:
                chunks.append(r)

        return chunks

    def _vector_search(self, query_embedding: list[float], top_k: int) -> list[dict]:
        """Standard ChromaDB vector search with parent-child assembly."""
        results = self.vector_store.query(query_embedding, top_k)
        chunks = []
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
                    chunks.append({
                        "child_id": chunk_id,
                        "child_content": text,
                        "parent_content": parent_results["documents"][0],
                        "parent_id": parent_id,
                        "doc_id": metadata["doc_id"],
                        "page_number": metadata.get("page_number", 0),
                        "distance": distance
                    })
            else:
                chunks.append({
                    "parent_id": chunk_id,
                    "parent_content": text,
                    "doc_id": metadata["doc_id"],
                    "page_number": metadata.get("page_number", 0),
                    "distance": distance
                })

        # Fallback without distance filter
        if not chunks:
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
                        chunks.append({
                            "child_id": results_relaxed["ids"][0][i],
                            "child_content": text,
                            "parent_content": parent_results["documents"][0],
                            "parent_id": parent_id,
                            "doc_id": metadata["doc_id"],
                            "page_number": metadata.get("page_number", 0),
                            "distance": distance
                        })
                else:
                    chunks.append({
                        "parent_id": results_relaxed["ids"][0][i],
                        "parent_content": text,
                        "doc_id": metadata["doc_id"],
                        "page_number": metadata.get("page_number", 0),
                        "distance": distance
                    })

        return chunks

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
