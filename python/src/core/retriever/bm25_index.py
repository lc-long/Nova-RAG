"""BM25 keyword search indexer for hybrid retrieval.

Maintains an in-memory BM25 index per document, built at ingest time
and queried during retrieval for keyword matching.
"""
import re
import jieba
import pickle
from pathlib import Path
from typing import Optional


def _normalize_text(text: str) -> str:
    """Collapse 'digit + space + letter' into 'digit+letter' to bridge spacing gaps.

    Examples:
      '30 m'  -> '30m'
      '50 km' -> '50km'
      '限高 30 m' -> '限高30m'
    """
    return re.sub(r'(\d+)\s+([a-zA-Z]+)', r'\1\2', text)


class BM25Indexer:
    """BM25 index for keyword search across document chunks."""

    def __init__(self, persist_directory: str = "./vector_db"):
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.persist_dir / "bm25_index.pkl"
        # doc_id -> {"chunk_ids": [...], "corpus": [[tokenized sentences]], "bm25": BM25}
        self.doc_indexes: dict = {}
        self.chunk_id_to_doc: dict = {}  # chunk_id -> doc_id
        self.chunk_id_to_content: dict = {}  # chunk_id -> content (original, not normalized)
        self._load()

    def _load(self):
        """Load existing index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "rb") as f:
                    data = pickle.load(f)
                    self.doc_indexes = data.get("doc_indexes", {})
                    self.chunk_id_to_doc = data.get("chunk_id_to_doc", {})
                    self.chunk_id_to_content = data.get("chunk_id_to_content", {})
            except Exception:
                pass

    def _save(self):
        """Persist index to disk."""
        with open(self.index_file, "wb") as f:
            pickle.dump({
                "doc_indexes": self.doc_indexes,
                "chunk_id_to_doc": self.chunk_id_to_doc,
                "chunk_id_to_content": self.chunk_id_to_content,
            }, f)

    def add_chunks(self, chunks: list):
        """Build or update BM25 index for a set of chunks (one document)."""
        if not chunks:
            return

        doc_id = chunks[0].doc_id
        chunk_ids = [c.chunk_id for c in chunks]

        # Normalize content before tokenizing to eliminate spacing mismatches
        normalized_corpus = [_normalize_text(c.content) for c in chunks]
        tokenized_corpus = [list(jieba.cut(doc)) for doc in normalized_corpus]

        from rank_bm25 import BM25Okapi
        bm25 = BM25Okapi(tokenized_corpus)

        self.doc_indexes[doc_id] = {
            "chunk_ids": chunk_ids,
            "tokenized_corpus": tokenized_corpus,
            "bm25": bm25,
        }

        for c in chunks:
            self.chunk_id_to_doc[c.chunk_id] = doc_id
            self.chunk_id_to_content[c.chunk_id] = c.content

        self._save()

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search BM25 index, return [(chunk_id, score)] sorted by score descending."""
        # Normalize query to match indexed content
        normalized_query = _normalize_text(query)
        query_tokens = list(jieba.cut(normalized_query))
        all_results: dict[str, float] = {}

        for doc_id, idx_data in self.doc_indexes.items():
            bm25 = idx_data["bm25"]
            scores = bm25.get_scores(query_tokens)
            chunk_ids = idx_data["chunk_ids"]
            for chunk_id, score in zip(chunk_ids, scores):
                if score > 0:
                    # For duplicate chunk_ids across docs, keep the highest score
                    if chunk_id not in all_results or score > all_results[chunk_id]:
                        all_results[chunk_id] = score

        # Sort by score descending
        sorted_results = sorted(all_results.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def reset(self):
        """Clear all indexes."""
        self.doc_indexes.clear()
        self.chunk_id_to_doc.clear()
        self.chunk_id_to_content.clear()
        if self.index_file.exists():
            self.index_file.unlink()
