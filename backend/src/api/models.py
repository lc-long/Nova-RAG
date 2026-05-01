"""SQLAlchemy models for Nova-RAG business data."""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .database import Base


class Document(Base):
    """Document metadata stored in PostgreSQL."""
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


class Conversation(Base):
    """Chat conversation session."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("MessageModel", back_populates="conversation", cascade="all,delete-orphan", order_by="MessageModel.created_at")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MessageModel(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True, default="")
    sources = Column(JSONB, nullable=True)  # references/citations
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "reasoning": self.reasoning or "",
            "sources": self.sources or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
