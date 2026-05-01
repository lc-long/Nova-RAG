"""PostgreSQL + pgvector vector store with parent-child support."""
import os
from typing import Optional, List

from sqlalchemy import create_engine, text, Column, String, Integer, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/novarag")

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True)
    doc_id = Column(String, nullable=False, index=True)
    chunk_type = Column(String, nullable=False)
    parent_id = Column(String, nullable=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_pgvector():
    """Create pgvector extension and all tables. Called once at startup."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)


class VectorStore:
    """PostgreSQL + pgvector store with persistent storage."""

    def __init__(self, **kwargs):
        pass

    def add_chunks(self, chunks: list, embeddings: list[list[float]], source: str = "") -> None:
        """Add chunks with their embeddings using a database transaction."""
        if not chunks or not embeddings:
            return

        session = SessionLocal()
        try:
            for chunk, embedding in zip(chunks, embeddings):
                row = DocumentChunk(
                    id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    chunk_type=chunk.chunk_type,
                    parent_id=chunk.parent_id or None,
                    content=chunk.content,
                    embedding=embedding,
                    metadata_={
                        "page_number": chunk.page_number or 0,
                        "order": chunk.order,
                        "source": source,
                        "heading_path": chunk.heading_path,
                    },
                )
                session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def query(self, query_embedding: list[float], top_k: int = 5, doc_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> dict:
        """Query for similar chunks using cosine distance, optionally filtered by doc_id(s).

        Returns a dict matching the interface expected by hybrid_search.py:
        {"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
        """
        session = SessionLocal()
        try:
            cosine_dist = DocumentChunk.embedding.cosine_distance(query_embedding)
            q = session.query(
                DocumentChunk.id,
                DocumentChunk.content,
                DocumentChunk.doc_id,
                DocumentChunk.chunk_type,
                DocumentChunk.parent_id,
                DocumentChunk.metadata_,
                cosine_dist.label("distance"),
            )
            if doc_ids:
                q = q.filter(DocumentChunk.doc_id.in_(doc_ids))
            elif doc_id:
                q = q.filter(DocumentChunk.doc_id == doc_id)
            q = q.order_by(cosine_dist).limit(top_k)
            rows = q.all()

            ids, documents, metadatas, distances = [], [], [], []
            for row in rows:
                ids.append(row.id)
                documents.append(row.content)
                metadatas.append({
                    "doc_id": row.doc_id,
                    "chunk_type": row.chunk_type,
                    "parent_id": row.parent_id or "",
                    "page_number": (row.metadata_ or {}).get("page_number", 0),
                    "source": (row.metadata_ or {}).get("source", ""),
                })
                distances.append(row.distance)

            return {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [distances],
            }
        finally:
            session.close()

    def get_by_parent(self, parent_id: str) -> dict:
        """Get all child chunks for a parent."""
        session = SessionLocal()
        try:
            rows = session.query(DocumentChunk).filter(
                DocumentChunk.parent_id == parent_id
            ).all()
            documents = [r.content for r in rows]
            return {"documents": documents}
        finally:
            session.close()

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks belonging to a document. Returns count of deleted chunks."""
        session = SessionLocal()
        try:
            count = session.query(DocumentChunk).filter(
                DocumentChunk.doc_id == doc_id
            ).delete()
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            print(f"[VectorStore] delete_by_doc_id error: {e}")
            return 0
        finally:
            session.close()
