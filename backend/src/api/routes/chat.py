"""Chat completion routes."""
import json
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...core.llm.minimax import Message

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = True
    doc_id: Optional[str] = None


@router.post("/completions")
async def chat_completions(request: Request, body: ChatRequest):
    """SSE streaming chat - mirrors Go's ChatHandler.Completions."""
    components = request.app.state.components
    if not components.llm_client or not components.retriever:
        raise HTTPException(status_code=500, detail="Service not initialized")

    messages = [Message(role=m.role, content=m.content) for m in body.messages]
    last_query = messages[-1].content if messages else ""

    context_chunks = components.retriever.retrieve(last_query, top_k=5, doc_id=body.doc_id)
    if not context_chunks:
        context_chunks = []

    def generate():
        for chunk in components.llm_client.stream_chat(messages, context_chunks):
            if chunk.chunk_type == "done":
                yield f"data: {json.dumps({'done': True, 'references': chunk.references})}\n\n"
            elif chunk.chunk_type == "reasoning":
                yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk.content})}\n\n"
            elif chunk.chunk_type == "answer":
                yield f"data: {json.dumps({'type': 'answer', 'content': chunk.content})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")