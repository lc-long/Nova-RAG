"""Document management routes."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer

from ..database import get_db
from ..models import Document
from ...core.storage.vector_store import DocumentChunk

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
    """Background ingestion task with optional OCR for images."""
    from ...core.chunker.pdf_parser import extract_text_from_pdf, extract_text_from_pdf_with_pages, merge_ocr_into_text
    from ...core.chunker.docx_parser import extract_text_from_docx
    from ...core.chunker.excel_parser import extract_text_from_excel
    from ...core.chunker.csv_parser import extract_text_from_csv
    from ...core.chunker.ppt_parser import extract_text_from_pptx
    from ...core.ocr import process_pdf_images

    try:
        if filename.endswith(".pdf"):
            # Extract page-by-page text for proper OCR association
            pages = extract_text_from_pdf_with_pages(file_path)

            # Process images with OCR
            try:
                image_results = process_pdf_images(file_path, doc_id)
                if image_results:
                    print(f"[DocsUpload] OCR: Found {len(image_results)} images with descriptions")
                    text = merge_ocr_into_text(pages, image_results)
                else:
                    text = "\n\n".join(t for _, t in pages if t.strip())
            except Exception as e:
                print(f"[DocsUpload] OCR processing failed (non-fatal): {e}")
                text = "\n\n".join(t for _, t in pages if t.strip())
                
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


@router.get("/{doc_id}/content")
async def get_document_content(doc_id: str, db: Session = Depends(get_db)):
    """Get full document content assembled from chunks."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from ..database import SessionLocal
    session = SessionLocal()
    try:
        chunks = session.query(DocumentChunk).filter(
            DocumentChunk.doc_id == doc_id
        ).all()

        # Sort by order in metadata
        def sort_key(c):
            meta = c.metadata_ or {}
            return meta.get("order", 0)
        chunks.sort(key=sort_key)

        # Strip source prefix from each chunk
        full_text = ""
        for c in chunks:
            text = c.content
            if text.startswith("[来源文件："):
                idx = text.find("]\n")
                if idx != -1:
                    text = text[idx + 2:]
            full_text += text + "\n\n"
    finally:
        session.close()

    return {
        "doc_id": doc_id,
        "name": doc.name,
        "status": doc.status,
        "content": full_text.strip(),
    }


def _resolve_file(doc_id: str, db: Session):
    """Shared helper: validate doc exists and return (doc, file_path, media_type)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    matches = list(UPLOAD_DIR.glob(f"{doc_id}_*"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found on disk")

    file_path = matches[0]
    suffix = file_path.suffix.lower()

    media_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/plain; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    media_type = media_types.get(suffix, "application/octet-stream")
    return doc, file_path, media_type


@router.get("/{doc_id}/preview")
async def preview_document(doc_id: str, db: Session = Depends(get_db)):
    """Serve the original file for inline preview (never triggers download)."""
    doc, file_path, media_type = _resolve_file(doc_id, db)
    encoded_name = quote(doc.name)
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_name}",
            "Content-Type": media_type,
        },
    )


@router.get("/{doc_id}/download")
async def download_document(doc_id: str, db: Session = Depends(get_db)):
    """Serve the original file as an attachment download."""
    doc, file_path, media_type = _resolve_file(doc_id, db)
    encoded_name = quote(doc.name)
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "Content-Type": media_type,
        },
    )


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