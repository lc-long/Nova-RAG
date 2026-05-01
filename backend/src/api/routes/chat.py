"""Chat completion routes."""
import json
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...core.llm.minimax import Message
from ..database import get_db
from ..models import Conversation, MessageModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = True
    doc_id: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None


@router.post("/completions")
async def chat_completions(request: Request, body: ChatRequest):
    """SSE streaming chat with optional doc_ids scoping and conversation persistence."""
    components = request.app.state.components
    if not components.llm_client or not components.retriever:
        raise HTTPException(status_code=500, detail="Service not initialized")

    # Resolve effective doc_ids: explicit list takes priority over single doc_id
    effective_doc_ids = body.doc_ids if body.doc_ids else ([body.doc_id] if body.doc_id else None)

    messages = [Message(role=m.role, content=m.content) for m in body.messages]
    last_query = messages[-1].content if messages else ""

    # Retrieve context — pass doc_ids list for multi-doc scoping
    if effective_doc_ids and len(effective_doc_ids) == 1:
        context_chunks = components.retriever.retrieve(last_query, top_k=5, doc_id=effective_doc_ids[0])
    elif effective_doc_ids and len(effective_doc_ids) > 1:
        context_chunks = components.retriever.retrieve_multi_docs(last_query, top_k=5, doc_ids=effective_doc_ids)
    else:
        context_chunks = components.retriever.retrieve(last_query, top_k=5)
    if not context_chunks:
        context_chunks = []

    # Ensure conversation exists
    conversation_id = body.conversation_id
    if conversation_id:
        db = next(get_db())
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            conversation_id = None
        db.close()

    if not conversation_id:
        db = next(get_db())
        conv = Conversation(
            id=str(uuid.uuid4()),
            title=last_query[:50] if last_query else "New Chat",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(conv)
        db.commit()
        conversation_id = conv.id
        db.close()

    # Save user message
    db = next(get_db())
    user_msg = MessageModel(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=last_query,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)
    db.commit()
    db.close()

    def generate():
        full_answer = ""
        full_reasoning = ""
        full_thought = ""
        references = []

        # --- Thought: retrieval phase ---
        doc_scope = "全局" if not effective_doc_ids else f"{len(effective_doc_ids)} 个指定文档"
        thought1 = f"🔍 正在进行语义向量检索（范围：{doc_scope}）..."
        full_thought += thought1 + "\n"
        yield f"data: {json.dumps({'type': 'thought', 'content': thought1})}\n\n"

        if context_chunks:
            thought2 = f"✅ 成功召回并重排 {len(context_chunks)} 个文档片段，开始生成回答..."
        else:
            thought2 = "⚠️ 未找到相关文档片段，将基于通用知识回答..."
        full_thought += thought2 + "\n"
        yield f"data: {json.dumps({'type': 'thought', 'content': thought2})}\n\n"

        # --- LLM streaming ---
        for chunk in components.llm_client.stream_chat(messages, context_chunks):
            if chunk.chunk_type == "done":
                references = chunk.references or []
                yield f"data: {json.dumps({'done': True, 'references': references, 'conversation_id': conversation_id})}\n\n"

                # Save assistant message
                db = next(get_db())
                assistant_msg = MessageModel(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_answer,
                    reasoning=full_reasoning,
                    sources=references,
                    created_at=datetime.utcnow(),
                )
                db.add(assistant_msg)

                conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
                if conv:
                    conv.updated_at = datetime.utcnow()
                    msg_count = db.query(MessageModel).filter(MessageModel.conversation_id == conversation_id).count()
                    if msg_count <= 1:
                        conv.title = last_query[:50]
                db.commit()
                db.close()

            elif chunk.chunk_type == "reasoning":
                full_reasoning += chunk.content
                yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.content})}\n\n"
            elif chunk.chunk_type == "answer":
                full_answer += chunk.content
                yield f"data: {json.dumps({'type': 'answer', 'content': chunk.content})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
