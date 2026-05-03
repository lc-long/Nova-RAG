"""Citation feedback routes for user ratings on reference quality."""
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("nova_rag")

router = APIRouter(prefix="/citations", tags=["citations"])

FEEDBACK_DIR = Path(__file__).parent.parent.parent.parent / "vector_db" / "citation_feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


class CitationFeedback(BaseModel):
    helpful: bool
    conversation_id: str
    query: str
    citation_index: int
    doc_id: str
    content: str


@router.post("/feedback")
async def submit_citation_feedback(feedback: CitationFeedback):
    """Store citation feedback (helpful/not helpful) for analytics."""
    try:
        feedback_file = FEEDBACK_DIR / f"{feedback.conversation_id}.jsonl"
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "helpful": feedback.helpful,
            "conversation_id": feedback.conversation_id,
            "query": feedback.query,
            "citation_index": feedback.citation_index,
            "doc_id": feedback.doc_id,
            "content_preview": feedback.content[:100],
        }
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(__import__("json").dumps(entry, ensure_ascii=False) + "\n")
        return {"status": "ok", "id": entry["id"]}
    except Exception as e:
        logger.error(f"[CitationFeedback] Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")


@router.get("/stats/{conversation_id}")
async def get_citation_stats(conversation_id: str):
    """Get citation statistics for a conversation."""
    feedback_file = FEEDBACK_DIR / f"{conversation_id}.jsonl"
    if not feedback_file.exists():
        return {"total": 0, "helpful": 0, "not_helpful": 0, "by_citation": {}}

    try:
        stats = {"total": 0, "helpful": 0, "not_helpful": 0, "by_citation": {}}
        with open(feedback_file, "r", encoding="utf-8") as f:
            for line in f:
                import json
                entry = json.loads(line.strip())
                stats["total"] += 1
                if entry["helpful"]:
                    stats["helpful"] += 1
                else:
                    stats["not_helpful"] += 1
                cit_key = str(entry["citation_index"])
                if cit_key not in stats["by_citation"]:
                    stats["by_citation"][cit_key] = {"helpful": 0, "not_helpful": 0}
                if entry["helpful"]:
                    stats["by_citation"][cit_key]["helpful"] += 1
                else:
                    stats["by_citation"][cit_key]["not_helpful"] += 1
        return stats
    except Exception as e:
        logger.error(f"[CitationFeedback] Failed to read stats: {e}")
        return {"total": 0, "helpful": 0, "not_helpful": 0, "by_citation": {}}
