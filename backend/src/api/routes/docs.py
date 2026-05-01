"""Document management routes."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Document

router = APIRouter(prefix="/docs", tags=["documents"])

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Handle document upload - mirrors Go's DocsHandler.Upload."""
    doc_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"

    content = await file.read()
    size = len(content)
    with open(saved_path, "wb") as f:
        f.write(content)

    doc = Document(
        id=doc_id,
        name=file.filename,
        size=size,
        status="processing",
        created_at=datetime.utcnow()
    )
    db.add(doc)
    db.commit()

    background_tasks.add_task(run_ingestion, request.app.state.components, doc_id, file.filename, str(saved_path))

    return {
        "id": doc_id,
        "name": file.filename,
        "size": size,
        "status": "processing"
    }


def run_ingestion(components, doc_id: str, filename: str, file_path: str):
    """Background ingestion task."""
    from ...core.chunker.pdf_parser import extract_text_from_pdf
    from ...core.chunker.docx_parser import extract_text_from_docx
    from ...core.chunker.excel_parser import extract_text_from_excel
    from ...core.chunker.csv_parser import extract_text_from_csv
    from ...core.chunker.ppt_parser import extract_text_from_pptx

    try:
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        elif filename.endswith(".xlsx"):
            text = extract_text_from_excel(file_path)
        elif filename.endswith(".csv"):
            text = extract_text_from_csv(file_path)
        elif filename.endswith(".pptx"):
            text = extract_text_from_pptx(file_path)
        elif filename.endswith(".md") or filename.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            print(f"[DocsUpload] Unsupported file type: {filename}")
            return

        if filename.endswith(".md"):
            chunks = components.chunker.chunk_markdown(text, doc_id)
        else:
            chunks = components.chunker.chunk(text, doc_id)

        prefix = f"[来源文件：{filename}]\n"
        for chunk in chunks:
            chunk.content = prefix + chunk.content

        embeddings = components.embedder.embed([c.content for c in chunks])
        components.vector_store.add_chunks(chunks, embeddings, source=filename)
        components.bm25_indexer.add_chunks(chunks)

        # Update status
        session = next(get_db())
        doc = session.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "ready"
            session.commit()
        session.close()
        print(f"[DocsUpload] Ingestion completed for {filename}")

    except Exception as e:
        print(f"[DocsUpload] Ingestion failed for {filename}: {e}")
        try:
            session = next(get_db())
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.status = "failed"
                session.commit()
            session.close()
        except Exception:
            pass


@router.get("")
async def list_documents(db: Session = Depends(get_db)):
    """List all documents - mirrors Go's DocsHandler.List."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [doc.to_dict() for doc in docs]


class BatchDeleteRequest(BaseModel):
    doc_ids: List[str]


@router.post("/batch-delete")
async def batch_delete_documents(request: Request, body: BatchDeleteRequest, db: Session = Depends(get_db)):
    """Delete multiple documents and their vectors in one transaction."""
    deleted = 0
    for doc_id in body.doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            db.delete(doc)
        for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
            f.unlink()
        try:
            request.app.state.components.vector_store.delete_by_doc_id(doc_id)
        except Exception as e:
            print(f"[BatchDelete] Vector cleanup failed for {doc_id}: {e}")
        deleted += 1
    db.commit()
    return {"status": "ok", "deleted": deleted}


@router.delete("/{doc_id}")
async def delete_document(request: Request, doc_id: str, db: Session = Depends(get_db)):
    """Delete document - mirrors Go's DocsHandler.Delete."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        print(f"[DeleteDoc] Warning: Document {doc_id} not found in DB, cleaning up vectors anyway")
    else:
        db.delete(doc)
        db.commit()

    for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink()

    try:
        request.app.state.components.vector_store.delete_by_doc_id(doc_id)
    except Exception as e:
        print(f"[DeleteDoc] Warning: Vector cleanup failed for {doc_id}: {e}")

    return {"status": "ok"}