"""Async hybrid retriever combining dense (pgvector) and sparse (BM25) search.

Uses Reciprocal Rank Fusion (RRF) to merge results from both engines.
Supports multi-query expansion via QueryRewriter to bridge vocabulary gaps.
Vector and BM25 searches run in parallel via asyncio.gather().
Includes Self-Query for metadata-aware retrieval.
"""
import asyncio
import logging
import re
from typing import Optional

from .bm25_index import BM25Indexer, _normalize_text
from .query_rewriter import QueryRewriter
from .aliyun_reranker import AliyunReranker
from .self_query import SelfQueryRetriever, MetadataFilter
from ..config import (
    RECALL_MULTIPLIER, RETRIEVER_TOP_K, RRF_K, MISSING_RANK, DISTANCE_THRESHOLD,
)

logger = logging.getLogger("nova_rag")


class HybridRetriever:
    """Async hybrid retriever using vector + BM25 with RRF fusion."""

    IMAGE_QUERY_KEYWORDS = [
        '图片', '图像', '照片', '截图', 'pic', 'image', 'photo', 'picture',
        '图表', 'fig', 'figure', 'diagram', '截图', '架构图', '流程图',
        'show me', 'what is this', '这是什么', '图片中', '图像中',
        '这张图', '那张图', '哪个图', '这个图', '那张', '哪个',
        '第几页', '页的图', '页图', 'page image', 'img ', 'img:',
        '看图', '看这张', '查看图', '展示', 'display', 'visual',
        '截图', '截图表', '屏幕截图', '画面', '画面中',
        '架构', '结构', '示意', '示意图',
    ]

    def __init__(
        self,
        vector_store,
        embedder,
        bm25_indexer: Optional[BM25Indexer] = None,
        distance_threshold: float = DISTANCE_THRESHOLD,
        rrf_k: int = RRF_K,
        rewriter: Optional[QueryRewriter] = None,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.bm25_indexer = bm25_indexer
        self.distance_threshold = distance_threshold
        self.rrf_k = rrf_k
        self.rewriter = rewriter or QueryRewriter()
        self.reranker = AliyunReranker()
        self.self_query = SelfQueryRetriever()

    def _is_image_query(self, query: str) -> bool:
        """Check if query is likely about images."""
        q_lower = query.lower()
        return any(kw in q_lower for kw in self.IMAGE_QUERY_KEYWORDS)

    async def retrieve_image_chunks(self, query: str, top_k: int = 5, doc_id: Optional[str] = None, doc_ids: Optional[list] = None) -> list[dict]:
        """Retrieve image chunks by searching their descriptions."""
        try:
            query_embedding = await asyncio.to_thread(self.embedder.embed, [query])
            query_embedding = query_embedding[0]

            if doc_ids:
                image_results = await asyncio.to_thread(self.vector_store.query_images, query_embedding, top_k * 2, doc_ids=doc_ids)
            elif doc_id:
                image_results = await asyncio.to_thread(self.vector_store.query_images, query_embedding, top_k * 2, doc_id=doc_id)
            else:
                image_results = await asyncio.to_thread(self.vector_store.query_images, query_embedding, top_k * 2)

            if not image_results:
                return []

            return image_results[:top_k]
        except Exception as e:
            logger.warning(f"[HybridRetriever] Image retrieval failed: {e}")
            return []

    async def retrieve(self, query: str, top_k: int = 5, doc_id: Optional[str] = None) -> list[dict]:
        """Async hybrid search with self-query, multi-query expansion, and RRF fusion."""
        # Step 1: Self-Query - parse user intent and metadata filters
        sq_result = await self.self_query.parse_query(query)
        semantic_query = sq_result.semantic_query
        filters = sq_result.filters

        # Step 2: Query expansion on the semantic query
        rewritten_queries = await self.rewriter.rewrite_with_fallback(semantic_query)
        if len(rewritten_queries) > 10:
            rewritten_queries = rewritten_queries[:10]

        recall_k = max(top_k * RECALL_MULTIPLIER, RETRIEVER_TOP_K)

        # Step 3: Determine search scope (metadata filter or doc_id)
        effective_doc_id = doc_id
        if not effective_doc_id and filters.doc_name_pattern:
            # Try to find matching document by name pattern
            effective_doc_id = self._find_doc_by_name(filters.doc_name_pattern)

        # Step 4: Vector + BM25 retrieval
        file_match = re.search(r'([^\s/\\]+\.(?:pdf|docx))', semantic_query, re.IGNORECASE)

        if file_match:
            filename_hint = file_match.group(1).lower()
            dense_task = self._metadata_search(filename_hint, recall_k, effective_doc_id)
        else:
            dense_task = self._multi_query_vector_search(rewritten_queries, recall_k, effective_doc_id)

        sparse_task = self._multi_query_bm25_search(rewritten_queries, recall_k, effective_doc_id)

        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

        # Step 5: RRF Fusion
        fused = self._rrf_fuse(dense_results, sparse_results, RETRIEVER_TOP_K)

        # Step 6: Apply page range filter if specified
        if filters.page_range:
            fused = self._filter_by_page_range(fused, filters.page_range)

        # Step 7: Rerank
        reranked = await self.reranker.rerank(semantic_query, fused, top_k=RETRIEVER_TOP_K)
        return reranked

    def _find_doc_by_name(self, pattern: str) -> Optional[str]:
        """Find document ID by name pattern (case-insensitive substring match)."""
        try:
            from ...api.database import SessionLocal
            from ...api.models import Document as DocModel

            session = SessionLocal()
            try:
                docs = session.query(DocModel).all()
                pattern_lower = pattern.lower()
                for doc in docs:
                    if pattern_lower in doc.name.lower():
                        logger.info(f"[SelfQuery] Matched doc '{doc.name}' for pattern '{pattern}'")
                        return doc.id
                logger.info(f"[SelfQuery] No doc matched pattern '{pattern}'")
                return None
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"[SelfQuery] Doc lookup failed: {e}")
            return None

    def _filter_by_page_range(self, chunks: list[dict], page_range: tuple[int, int]) -> list[dict]:
        """Filter chunks by page number range."""
        start_page, end_page = page_range
        filtered = []
        for chunk in chunks:
            page = chunk.get("page_number", 0)
            if page == 0 or (start_page <= page <= end_page):
                filtered.append(chunk)
        if filtered:
            logger.info(f"[SelfQuery] Page filter {page_range}: {len(chunks)} → {len(filtered)} chunks")
            return filtered
        return chunks  # If all filtered out, return original

    async def retrieve_multi_docs(self, query: str, top_k: int = 5, doc_ids: list[str] = None) -> list[dict]:
        """Async hybrid search scoped to multiple doc_ids. Merges and deduplicates results."""
        if not doc_ids:
            return await self.retrieve(query, top_k)

        tasks = [self.retrieve(query, top_k, doc_id=did) for did in doc_ids]
        all_doc_results = await asyncio.gather(*tasks)

        all_results: list[dict] = []
        seen_keys: set[str] = set()

        for results in all_doc_results:
            for r in results:
                key = r.get("child_id") or r.get("parent_id")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_results.append(r)

        all_results.sort(key=lambda r: r.get("rerank_score", 0), reverse=True)
        return all_results[:RETRIEVER_TOP_K]

    async def _multi_query_vector_search(self, queries: list[str], top_k: int, doc_id: Optional[str] = None) -> list[dict]:
        """Run vector search across multiple query variants, merge results."""
        chunk_best: dict[str, dict] = {}

        for q in queries:
            normalized_q = _normalize_text(q)
            query_embedding = await asyncio.to_thread(self.embedder.embed, [normalized_q])
            query_embedding = query_embedding[0]
            results = await self._vector_search(query_embedding, top_k, doc_id)
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

    async def _multi_query_bm25_search(self, queries: list[str], top_k: int, doc_id: Optional[str] = None) -> list[dict]:
        """Run BM25 search across multiple query variants, merge by best score."""
        chunk_best_score: dict[str, float] = {}

        for q in queries:
            results = await asyncio.to_thread(self.bm25_indexer.search, q, top_k=top_k, doc_id=doc_id)
            for chunk_id, score in results:
                if chunk_id not in chunk_best_score or score > chunk_best_score[chunk_id]:
                    chunk_best_score[chunk_id] = score

        sorted_results = sorted(chunk_best_score.items(), key=lambda x: x[1], reverse=True)

        sparse_results = []
        for chunk_id, bm25_score in sorted_results[:top_k]:
            content = self.bm25_indexer.chunk_id_to_content.get(chunk_id, "")
            result_doc_id = self.bm25_indexer.chunk_id_to_doc.get(chunk_id, "")
            sparse_results.append({
                "child_id": None,
                "parent_id": chunk_id,
                "child_content": "",
                "parent_content": content,
                "doc_id": result_doc_id,
                "page_number": 0,
                "bm25_score": bm25_score,
            })

        return sparse_results

    def _rrf_fuse(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
        top_k: int
    ) -> list[dict]:
        """Reciprocal Rank Fusion using rank-based scoring."""
        sorted_dense = sorted(dense_results, key=lambda r: r.get("distance", float("inf")))
        dense_rank: dict[str, int] = {}
        for rank, result in enumerate(sorted_dense, start=1):
            key = result.get("child_id") or result.get("parent_id")
            if key:
                dense_rank[key] = rank

        sorted_sparse = sorted(sparse_results, key=lambda r: r.get("bm25_score", 0), reverse=True)
        sparse_rank: dict[str, int] = {}
        for rank, result in enumerate(sorted_sparse, start=1):
            key = result.get("child_id") or result.get("parent_id")
            if key:
                sparse_rank[key] = rank

        all_keys = set(dense_rank.keys()) | set(sparse_rank.keys())

        rrf_scores: dict[str, float] = {}
        for key in all_keys:
            d_rank = dense_rank.get(key, MISSING_RANK)
            s_rank = sparse_rank.get(key, MISSING_RANK)
            rrf_scores[key] = (1.0 / (self.rrf_k + d_rank)) + (1.0 / (self.rrf_k + s_rank))

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

    def _assemble_chunk(self, chunk_id: str, metadata: dict, text: str, distance: float) -> dict:
        """Assemble a single chunk result dict from vector search data."""
        if metadata["chunk_type"] == "child":
            return {
                "_type": "child",
                "child_id": chunk_id,
                "child_content": text,
                "parent_id": metadata["parent_id"],
                "doc_id": metadata["doc_id"],
                "page_number": metadata.get("page_number", 0),
                "distance": distance,
            }
        else:
            return {
                "_type": "parent",
                "parent_id": chunk_id,
                "parent_content": text,
                "doc_id": metadata["doc_id"],
                "page_number": metadata.get("page_number", 0),
                "distance": distance,
            }

    async def _resolve_parent_content(self, chunks: list[dict]) -> list[dict]:
        """Resolve parent content for child chunks, filter duplicates."""
        seen_parent_ids = set()
        seen_texts = set()
        resolved = []

        for r in chunks:
            text = r.get("child_content") or r.get("parent_content", "")
            norm_text = text.replace("\n", " ").strip()
            if norm_text in seen_texts:
                continue
            seen_texts.add(norm_text)

            if r["_type"] == "child":
                parent_id = r["parent_id"]
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)
                parent_results = await asyncio.to_thread(self.vector_store.get_by_parent, parent_id)
                if parent_results["documents"]:
                    resolved.append({
                        "child_id": r["child_id"],
                        "child_content": r["child_content"],
                        "parent_content": parent_results["documents"][0],
                        "parent_id": parent_id,
                        "doc_id": r["doc_id"],
                        "page_number": r["page_number"],
                        "distance": r["distance"],
                    })
            else:
                resolved.append({
                    "parent_id": r["parent_id"],
                    "parent_content": r["parent_content"],
                    "doc_id": r["doc_id"],
                    "page_number": r["page_number"],
                    "distance": r["distance"],
                })

        return resolved

    async def _vector_search(self, query_embedding: list[float], top_k: int, doc_id: Optional[str] = None) -> list[dict]:
        """Async pgvector search with parent-child assembly."""
        results = await asyncio.to_thread(self.vector_store.query, query_embedding, top_k, doc_id=doc_id)

        raw_chunks = []
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            if distance > self.distance_threshold:
                continue
            text = results["documents"][0][i]
            raw_chunks.append(self._assemble_chunk(chunk_id, metadata, text, distance))

        chunks = await self._resolve_parent_content(raw_chunks)

        if not chunks:
            results_relaxed = await asyncio.to_thread(self.vector_store.query, query_embedding, top_k)
            raw_chunks_relaxed = []
            for i in range(len(results_relaxed["ids"][0])):
                chunk_id = results_relaxed["ids"][0][i]
                metadata = results_relaxed["metadatas"][0][i]
                distance = results_relaxed["distances"][0][i]
                text = results_relaxed["documents"][0][i]
                raw_chunks_relaxed.append(self._assemble_chunk(chunk_id, metadata, text, distance))
            chunks = await self._resolve_parent_content(raw_chunks_relaxed)

        return chunks

    async def _metadata_search(self, filename_hint: str, top_k: int, doc_id: Optional[str] = None) -> list[dict]:
        """Search by source metadata containing filename hint using PostgreSQL."""
        try:
            from ..storage.vector_store import DocumentChunk
            from ...api.database import SessionLocal

            def _do_metadata_search():
                session = SessionLocal()
                try:
                    q = session.query(DocumentChunk).filter(
                        DocumentChunk.metadata_["source"].astext.ilike(f"%{filename_hint}%")
                    )
                    if doc_id:
                        q = q.filter(DocumentChunk.doc_id == doc_id)
                    return q.limit(top_k).all()
                finally:
                    session.close()

            rows = await asyncio.to_thread(_do_metadata_search)

            results = []
            seen_parent_ids = set()
            for row in rows:
                meta = row.metadata_ or {}
                if meta.get("chunk_type") == "child":
                    parent_id = meta.get("parent_id")
                    if parent_id in seen_parent_ids:
                        continue
                    seen_parent_ids.add(parent_id)
                    parent_results = await asyncio.to_thread(self.vector_store.get_by_parent, parent_id)
                    if parent_results["documents"]:
                        results.append({
                            "child_id": row.id,
                            "child_content": row.content,
                            "parent_content": parent_results["documents"][0],
                            "parent_id": parent_id,
                            "doc_id": row.doc_id,
                            "page_number": meta.get("page_number", 0),
                            "distance": 0.0,
                        })
                else:
                    results.append({
                        "parent_id": row.id,
                        "parent_content": row.content,
                        "doc_id": row.doc_id,
                        "page_number": meta.get("page_number", 0),
                        "distance": 0.0,
                    })
            return results[:top_k]
        except Exception as e:
            logger.warning(f"[HybridRetriever] Metadata search failed: {e}")
            return []
