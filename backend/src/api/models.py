"""SQLAlchemy models for Nova-RAG business data."""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from .database import Base


class Document(Base):
    """Document metadata stored in SQLite."""
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    status = Column(String, default="processing")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }