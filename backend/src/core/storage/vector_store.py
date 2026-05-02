"""PostgreSQL + pgvector vector store with parent-child support."""
from typing import Optional, List
from dataclasses import dataclass

from sqlalchemy import text, Column, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime

# Reuse the shared engine/session from database module (single connection pool)
from ...api.database import engine, SessionLocal, Base


@dataclass
class ImageChunkData:
    chunk_id: str
    doc_id: str
    page_num: int
    image_idx: int
    description: str
    image_path: str
    metadata: dict = None


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


class ImageChunk(Base):
    __tablename__ = "image_chunks"

    id = Column(String, primary_key=True)
    doc_id = Column(String, nullable=False, index=True)
    page_num = Column(Integer, nullable=False)
    image_idx = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=False)
    image_path = Column(String, nullable=False)
    embedding = Column(Vector(1024), nullable=True)
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

    def add_image_chunks(self, image_chunks: list[ImageChunkData], embeddings: list[list[float]] = None) -> None:
        """Add image chunks with optional embeddings."""
        if not image_chunks:
            return
        session = SessionLocal()
        try:
            for i, img_chunk in enumerate(image_chunks):
                row = ImageChunk(
                    id=img_chunk.chunk_id,
                    doc_id=img_chunk.doc_id,
                    page_num=img_chunk.page_num,
                    image_idx=img_chunk.image_idx,
                    description=img_chunk.description,
                    image_path=img_chunk.image_path,
                    embedding=embeddings[i] if embeddings and i < len(embeddings) else None,
                    metadata_=img_chunk.metadata or {},
                )
                session.add(row)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def query_images(self, query_embedding: list[float], top_k: int = 5, doc_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> list[dict]:
        """Query for similar image chunks using cosine distance."""
        session = SessionLocal()
        try:
            cosine_dist = ImageChunk.embedding.cosine_distance(query_embedding)
            q = session.query(
                ImageChunk.id,
                ImageChunk.doc_id,
                ImageChunk.page_num,
                ImageChunk.image_idx,
                ImageChunk.description,
                ImageChunk.image_path,
                ImageChunk.metadata_,
                cosine_dist.label("distance"),
            )
            if doc_ids:
                q = q.filter(ImageChunk.doc_id.in_(doc_ids))
            elif doc_id:
                q = q.filter(ImageChunk.doc_id == doc_id)
            q = q.order_by(cosine_dist).limit(top_k)
            rows = q.all()

            results = []
            for row in rows:
                results.append({
                    "chunk_id": row.id,
                    "doc_id": row.doc_id,
                    "page_num": row.page_num,
                    "image_idx": row.image_idx,
                    "description": row.description,
                    "image_path": row.image_path,
                    "distance": row.distance,
                    "metadata": row.metadata_ or {},
                })
            return results
        finally:
            session.close()

    def get_image_chunks_by_doc_id(self, doc_id: str) -> list[dict]:
        """Get all image chunks for a document."""
        session = SessionLocal()
        try:
            rows = session.query(ImageChunk).filter(ImageChunk.doc_id == doc_id).all()
            return [{
                "chunk_id": row.id,
                "doc_id": row.doc_id,
                "page_num": row.page_num,
                "image_idx": row.image_idx,
                "description": row.description,
                "image_path": row.image_path,
                "metadata": row.metadata_ or {},
            } for row in rows]
        finally:
            session.close()

    def delete_image_chunks_by_doc_id(self, doc_id: str) -> int:
        """Delete all image chunks for a document."""
        session = SessionLocal()
        try:
            count = session.query(ImageChunk).filter(ImageChunk.doc_id == doc_id).delete()
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            print(f"[VectorStore] delete_image_chunks_by_doc_id error: {e}")
            return 0
        finally:
            session.close()
