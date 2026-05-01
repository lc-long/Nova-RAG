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

# Token limits
MAX_CONTEXT_TOKENS = 4000
MAX_HISTORY_TOKENS = 2000


def estimate_tokens(text: str) -> int:
    """Estimate token count with better CJK handling.

    Heuristic: Chinese chars ≈ 1.5 tokens each, other chars ≈ 0.25 tokens each.
    This is much more accurate than len/4 for mixed Chinese-English text.
    """
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.25)


def truncate_messages(messages: List[Message], max_tokens: int) -> List[Message]:
    """Keep most recent messages within token limit."""
    if not messages:
        return messages

    total_tokens = 0
    truncated = []
    # Process from newest to oldest
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg.content)
        if total_tokens + msg_tokens > max_tokens:
            break
        truncated.insert(0, msg)
        total_tokens += msg_tokens

    # Always keep at least the last user message
    if not truncated and messages:
        truncated = [messages[-1]]

    return truncated


def truncate_context(chunks: list, max_tokens: int) -> list:
    """Keep top chunks within token limit."""
    if not chunks:
        return chunks

    total_tokens = 0
    truncated = []
    for chunk in chunks:
        content = chunk.get("parent_content", "") or chunk.get("content", "")
        chunk_tokens = estimate_tokens(content)
        if total_tokens + chunk_tokens > max_tokens:
            break
        truncated.append(chunk)
        total_tokens += chunk_tokens

    return truncated


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

    # Build messages with history
    all_messages = [Message(role=m.role, content=m.content) for m in body.messages]
    last_query = all_messages[-1].content if all_messages else ""

    # Truncate history to fit token limit
    messages = truncate_messages(all_messages, MAX_HISTORY_TOKENS)

    # Retrieve context — pass doc_ids list for multi-doc scoping
    if effective_doc_ids and len(effective_doc_ids) == 1:
        context_chunks = components.retriever.retrieve(last_query, top_k=5, doc_id=effective_doc_ids[0])
    elif effective_doc_ids and len(effective_doc_ids) > 1:
        context_chunks = components.retriever.retrieve_multi_docs(last_query, top_k=5, doc_ids=effective_doc_ids)
    else:
        context_chunks = components.retriever.retrieve(last_query, top_k=5)
    if not context_chunks:
        context_chunks = []

    # Truncate context to fit token limit
    context_chunks = truncate_context(context_chunks, MAX_CONTEXT_TOKENS)

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
