"""Hybrid retriever combining dense (ChromaDB) and sparse (BM25) search.

Uses Reciprocal Rank Fusion (RRF) to merge results from both engines.
Supports multi-query expansion via QueryRewriter to bridge vocabulary gaps.
"""
import re
from typing import Optional

from .bm25_index import BM25Indexer, _normalize_text
from .query_rewriter import QueryRewriter
from .reranker import Reranker

# Scale-up constants: initial recall pool before RRF fusion
_RECALL_MULTIPLIER = 6   # top_k * 6 → initial召回量
_OUTPUT_TOP_K = 20        # RRF融合后输出量（扩大到20，给大模型更宽的上下文视野）
_RRF_K = 60              # RRF constant
_MISSING_RANK = 1000     # Large rank assigned to chunks appearing in only one channel


class HybridRetriever:
    """Hybrid retriever using vector + BM25 with RRF fusion."""

    def __init__(
        self,
        vector_store,
        embedder,
        bm25_indexer: Optional[BM25Indexer] = None,
        distance_threshold: float = 10.0,
        rrf_k: int = _RRF_K,
        rewriter: Optional[QueryRewriter] = None,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.bm25_indexer = bm25_indexer
        self.distance_threshold = distance_threshold
        self.rrf_k = rrf_k
        self.rewriter = rewriter or QueryRewriter()
        self.reranker = Reranker()

    def retrieve(self, query: str, top_k: int = 5, doc_id: Optional[str] = None) -> list[dict]:
        """Hybrid search: multi-query expanded vector + BM25 with RRF fusion.

        If doc_id is provided, scope search to that document only.
        Scaling: initial recall pool = top_k * 6 (30 when top_k=5),
        output after RRF = _OUTPUT_TOP_K (20).
        """
        # Rewrite query into multiple variants to bridge vocabulary gap
        rewritten_queries = self.rewriter.rewrite_with_fallback(query)
        if len(rewritten_queries) > 10:
            rewritten_queries = rewritten_queries[:10]

        # Internal scaling: always use expanded pool regardless of caller top_k
        recall_k = max(top_k * _RECALL_MULTIPLIER, _OUTPUT_TOP_K)

        # --- Vector (dense) retrieval across all query variants ---
        file_match = re.search(r'([^\s/\\]+\.(?:pdf|docx))', query, re.IGNORECASE)

        if file_match:
            filename_hint = file_match.group(1).lower()
            dense_results = self._metadata_search(filename_hint, recall_k)
        else:
            dense_results = self._multi_query_vector_search(rewritten_queries, recall_k, doc_id)

        # --- BM25 (sparse) retrieval across all query variants ---
        sparse_results = []
        if self.bm25_indexer:
            sparse_ids = self._multi_query_bm25_search(rewritten_queries, recall_k, doc_id)
            for chunk_id, bm25_score in sparse_ids:
                content = self.bm25_indexer.chunk_id_to_content.get(chunk_id, "")
                doc_id = self.bm25_indexer.chunk_id_to_doc.get(chunk_id, "")
                parent_id = ""
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
                    "bm25_score": bm25_score,
                })

        # --- RRF Fusion (rank-based, not score-based) ---
        fused = self._rrf_fuse(dense_results, sparse_results, _OUTPUT_TOP_K)

        # --- Cross-Encoder reranking: refine top-20 with deep semantic scoring ---
        reranked = self.reranker.rerank(query, fused, top_k=_OUTPUT_TOP_K)
        return reranked

    def _multi_query_vector_search(self, queries: list[str], top_k: int, doc_id: Optional[str] = None) -> list[dict]:
        """Run vector search across multiple query variants, merge results.

        If doc_id is provided, scope search to that document only.
        """
        chunk_best: dict[str, dict] = {}

        for q in queries:
            normalized_q = _normalize_text(q)
            query_embedding = self.embedder.embed([normalized_q])[0]
            results = self._vector_search(query_embedding, top_k, doc_id)
            for r in results:
                key = r.get("child_id") or r.get("parent_id")
                if key is None:
                    continue
                if key not in chunk_best:
                    chunk_best[key] = r
                else:
                    if r.get("distance", float("inf")) < chunk_best[key].get("distance", float("inf")):
                        chunk_best[key] = r

        return list(chunk_best.values())

    def _multi_query_bm25_search(self, queries: list[str], top_k: int, doc_id: Optional[str] = None) -> list[tuple[str, float]]:
        """Run BM25 search across multiple query variants, merge by best score.

        If doc_id is provided, search only that document's chunks.
        """
        chunk_best_score: dict[str, float] = {}

        for q in queries:
            results = self.bm25_indexer.search(q, top_k=top_k, doc_id=doc_id)
            for chunk_id, score in results:
                if chunk_id not in chunk_best_score or score > chunk_best_score[chunk_id]:
                    chunk_best_score[chunk_id] = score

        sorted_results = sorted(chunk_best_score.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def _rrf_fuse(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
        top_k: int
    ) -> list[dict]:
        """Reciprocal Rank Fusion using rank-based scoring (NOT distance/score).

        Correct RRF formula: score = 1/(k+rank)
        - Dense: sort by distance ASC, assign rank 1, 2, 3...
        - Sparse: sort by BM25 score DESC, assign rank 1, 2, 3...
        - Chunks in only one channel get rank=_MISSING_RANK for the other channel
        """
        # --- Build dense rank map (distance ASC -> rank) ---
        sorted_dense = sorted(dense_results, key=lambda r: r.get("distance", float("inf")))
        dense_rank: dict[str, int] = {}
        for rank, result in enumerate(sorted_dense, start=1):
            key = result.get("child_id") or result.get("parent_id")
            if key:
                dense_rank[key] = rank

        # --- Build sparse rank map (BM25 score DESC -> rank) ---
        sorted_sparse = sorted(sparse_results, key=lambda r: r.get("bm25_score", 0), reverse=True)
        sparse_rank: dict[str, int] = {}
        for rank, result in enumerate(sorted_sparse, start=1):
            key = result.get("child_id") or result.get("parent_id")
            if key:
                sparse_rank[key] = rank

        # --- Collect all unique chunk keys ---
        all_keys = set(dense_rank.keys()) | set(sparse_rank.keys())

        # --- Compute RRF scores using rank-based formula ---
        rrf_scores: dict[str, float] = {}
        for key in all_keys:
            d_rank = dense_rank.get(key, _MISSING_RANK)
            s_rank = sparse_rank.get(key, _MISSING_RANK)
            rrf_scores[key] = (1.0 / (self.rrf_k + d_rank)) + (1.0 / (self.rrf_k + s_rank))

        # Build result map with all metadata
        all_results: dict[str, dict] = {}
        for r in dense_results:
            key = r.get("child_id") or r.get("parent_id")
            if key:
                all_results[key] = r
        for r in sparse_results:
            key = r.get("child_id") or r.get("parent_id")
            if key:
                if key not in all_results:
                    all_results[key] = r

        # Sort by RRF score descending
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

    def _vector_search(self, query_embedding: list[float], top_k: int, doc_id: Optional[str] = None) -> list[dict]:
        """Standard ChromaDB vector search with parent-child assembly, optionally filtered by doc_id."""
        results = self.vector_store.query(query_embedding, top_k, doc_id=doc_id)
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
