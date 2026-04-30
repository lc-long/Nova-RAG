"""Document management routes -接管 Go 的 docs handler."""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Document
from ..components import vector_store, embedder, bm25_indexer, chunker

router = APIRouter(prefix="/docs", tags=["documents"])

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
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

    background_tasks.add_task(run_ingestion, doc_id, file.filename, str(saved_path))

    return {
        "id": doc_id,
        "name": file.filename,
        "size": size,
        "status": "processing"
    }


def run_ingestion(doc_id: str, filename: str, file_path: str):
    """Background ingestion task - mirrors Go's ingestToPython."""
    from ...core.chunker.pdf_parser import extract_text_from_pdf
    from ...core.chunker.docx_parser import extract_text_from_docx
    from ...core.chunker.excel_parser import extract_text_from_excel
    from ...core.chunker.csv_parser import extract_text_from_csv
    from ...core.chunker.ppt_parser import extract_text_from_pptx

    _vector_store = vector_store
    _embedder = embedder
    _bm25_indexer = bm25_indexer
    _chunker = chunker

    if not all([_vector_store, _embedder, _bm25_indexer, _chunker]):
        print(f"[DocsUpload] Components not initialized, skipping ingestion for {filename}")
        return

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
            chunks = _chunker.chunk_markdown(text, doc_id)
        else:
            chunks = _chunker.chunk(text, doc_id)

        prefix = f"[来源文件：{filename}]\n"
        for chunk in chunks:
            chunk.content = prefix + chunk.content

        embeddings = _embedder.embed([c.content for c in chunks])
        _vector_store.add_chunks(chunks, embeddings, source=filename)
        _bm25_indexer.add_chunks(chunks)

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


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete document - mirrors Go's DocsHandler.Delete."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink()

    _vector_store = vector_store
    if _vector_store:
        _vector_store.delete_by_doc_id(doc_id)

    db.delete(doc)
    db.commit()

    return {"status": "ok"}