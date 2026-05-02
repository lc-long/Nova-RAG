"""Conversation management routes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Conversation, MessageModel

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(db: Session = Depends(get_db)):
    """List all conversations, newest first."""
    convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    return [c.to_dict() for c in convs]


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"


@router.post("")
async def create_conversation(body: CreateConversationRequest, db: Session = Depends(get_db)):
    """Create a new conversation."""
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=str(uuid.uuid4()),
        title=body.title or "New Chat",
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    db.commit()
    return conv.to_dict()


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get a conversation with all its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = db.query(MessageModel).filter(
        MessageModel.conversation_id == conversation_id
    ).order_by(MessageModel.created_at).all()
    return {
        **conv.to_dict(),
        "messages": [m.to_dict() for m in messages],
    }


@router.patch("/{conversation_id}")
async def update_conversation(conversation_id: str, body: CreateConversationRequest, db: Session = Depends(get_db)):
    """Update conversation title."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if body.title:
        conv.title = body.title
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    return conv.to_dict()


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"status": "ok"}
