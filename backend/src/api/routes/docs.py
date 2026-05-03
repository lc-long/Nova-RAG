"""Document management routes."""
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db, get_db_session
from ..models import Document
from ...core.storage.vector_store import DocumentChunk

logger = logging.getLogger("nova_rag")

router = APIRouter(prefix="/docs", tags=["documents"])

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".pptx", ".md", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _secure_filename(filename: str) -> str:
    """Sanitize filename: strip path separators and dangerous characters."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = "".join(c for c in name if c.isalnum() or c in ".-_ ")
    return name[:200] if name else "unnamed"


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """Handle document upload with size and type validation."""
    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    # Read with size limit
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    size = len(content)
    doc_id = str(uuid.uuid4())
    safe_name = _secure_filename(file.filename or "unnamed")
    saved_path = UPLOAD_DIR / f"{doc_id}_{safe_name}"

    with open(saved_path, "wb") as f:
        f.write(content)

    doc = Document(
        id=doc_id,
        name=file.filename,
        size=size,
        status="processing",
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()

    if background_tasks is not None:
        background_tasks.add_task(run_ingestion, request.app.state.components, doc_id, file.filename, str(saved_path))

    return {
        "id": doc_id,
        "name": file.filename,
        "size": size,
        "status": "processing",
    }


def run_ingestion(components, doc_id: str, filename: str, file_path: str):
    """Background ingestion task with OCR for PDF images."""
    import asyncio
    from ...core.chunker.pdf_parser import extract_text_from_pdf_with_pages, merge_ocr_into_text
    from ...core.chunker.docx_parser import extract_text_from_docx
    from ...core.chunker.excel_parser import extract_text_from_excel
    from ...core.chunker.csv_parser import extract_text_from_csv
    from ...core.chunker.ppt_parser import extract_text_from_pptx
    from ...core.ocr import process_pdf_images
    from ...core.storage.vector_store import ImageChunkData
    import uuid

    db = get_db_session()
    try:
        ext = Path(filename).suffix.lower()
        ocr_results = []

        if ext == ".pdf":
            pages = extract_text_from_pdf_with_pages(file_path)
            text = "\n\n".join(t for _, t in pages if t.strip())

            try:
                ocr_results = asyncio.run(process_pdf_images(file_path, doc_id))
                if ocr_results:
                    text = merge_ocr_into_text(pages, ocr_results)
                    logger.info(f"[OCR] Merged {len(ocr_results)} image descriptions into text")
            except Exception as e:
                logger.warning(f"[OCR] Failed for {filename}: {e}")
        elif ext == ".docx":
            text = extract_text_from_docx(file_path)
        elif ext == ".xlsx":
            text = extract_text_from_excel(file_path)
        elif ext == ".csv":
            text = extract_text_from_csv(file_path)
        elif ext == ".pptx":
            text = extract_text_from_pptx(file_path)
        elif ext in (".md", ".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            logger.warning(f"[DocsUpload] Unsupported file type: {filename}")
            return

        if ext == ".md":
            chunks = components.chunker.chunk_markdown(text, doc_id)
        else:
            chunks = components.chunker.chunk(text, doc_id)

        safe_name = _secure_filename(filename)
        prefix = f"[来源文件：{safe_name}]\n"
        for chunk in chunks:
            chunk.content = prefix + chunk.content

        embeddings = components.embedder.embed([c.content for c in chunks])
        components.vector_store.add_chunks(chunks, embeddings, source=filename)
        components.bm25_indexer.add_chunks(chunks)

        # Store image chunks (OCR results with image paths)
        if ocr_results:
            image_chunks = []
            for img in ocr_results:
                img_chunk = ImageChunkData(
                    chunk_id=f"{doc_id}_img_{img.get('page_num', 0)}_{img.get('image_idx', 0)}",
                    doc_id=doc_id,
                    page_num=img.get('page_num', 0),
                    image_idx=img.get('image_idx', 0),
                    description=img.get('description', ''),
                    image_path=img.get('image_path', ''),
                    metadata={
                        'source': filename,
                        'width': img.get('width', 0),
                        'height': img.get('height', 0),
                    },
                )
                image_chunks.append(img_chunk)

            if image_chunks:
                desc_embeddings = components.embedder.embed([ic.description for ic in image_chunks])
                components.vector_store.add_image_chunks(image_chunks, desc_embeddings)
                logger.info(f"[OCR] Stored {len(image_chunks)} image chunks in DB")

        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "ready"
            db.commit()
        logger.info(f"[DocsUpload] Ingestion completed for {filename}")

    except Exception as e:
        logger.exception(f"[DocsUpload] Ingestion failed for {filename}: {e}")
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.status = "failed"
                db.commit()
        except Exception:
            logger.exception(f"[DocsUpload] Failed to update status for {doc_id}")
    finally:
        db.close()


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
            logger.warning(f"[BatchDelete] Vector cleanup failed for {doc_id}: {e}")
        deleted += 1
    db.commit()
    return {"status": "ok", "deleted": deleted}


@router.get("/{doc_id}/content")
async def get_document_content(doc_id: str, db: Session = Depends(get_db)):
    """Get full document content assembled from chunks."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.doc_id == doc_id
    ).all()

    def sort_key(c):
        meta = c.metadata_ or {}
        return meta.get("order", 0)
    chunks.sort(key=sort_key)

    full_text = ""
    chunk_positions = []
    current_pos = 0

    for idx, c in enumerate(chunks):
        text = c.content
        if text.startswith("[来源文件："):
            idx_marker = text.find("]\n")
            if idx_marker != -1:
                text = text[idx_marker + 2:]
        start_pos = current_pos
        full_text += text + "\n\n"
        end_pos = current_pos + len(text)
        current_pos = end_pos + 2

        meta = c.metadata_ or {}
        chunk_positions.append({
            "index": idx,
            "chunk_id": c.id,
            "content": text,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "order": meta.get("order", idx),
            "page_number": meta.get("page_number", 0),
        })

    return {
        "doc_id": doc_id,
        "name": doc.name,
        "status": doc.status,
        "content": full_text.strip(),
        "chunks": chunk_positions,
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


@router.get("/{doc_id}/images/{image_idx}")
async def get_document_image(doc_id: str, image_idx: int, db: Session = Depends(get_db)):
    """Serve an image file from the image storage directory."""
    import os
    from ...core.config import IMAGE_STORAGE_DIR

    image_dir = os.path.join(IMAGE_STORAGE_DIR, doc_id)

    if not os.path.exists(image_dir):
        raise HTTPException(status_code=404, detail="Image directory not found")

    image_chunks = request.app.state.components.vector_store.get_image_chunks_by_doc_id(doc_id)
    if not image_chunks:
        raise HTTPException(status_code=404, detail="No images found for this document")

    if image_idx < 0 or image_idx >= len(image_chunks):
        raise HTTPException(status_code=404, detail="Image index out of range")

    image_path = image_chunks[image_idx].get("image_path", "")
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image file not found")

    ext = os.path.splitext(image_path)[1].lower()
    media_type_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    media_type = media_type_map.get(ext, 'application/octet-stream')

    return FileResponse(
        path=image_path,
        media_type=media_type,
    )


@router.get("/{doc_id}/images")
async def list_document_images(doc_id: str, db: Session = Depends(get_db)):
    """List all images for a document."""
    image_chunks = request.app.state.components.vector_store.get_image_chunks_by_doc_id(doc_id)
    if not image_chunks:
        return {"images": []}

    return {
        "images": [
            {
                "idx": i,
                "page_num": img.get("page_num", 0),
                "description": img.get("description", ""),
                "image_path": img.get("image_path", ""),
            }
            for i, img in enumerate(image_chunks)
        ]
    }


@router.delete("/{doc_id}")
async def delete_document(request: Request, doc_id: str, db: Session = Depends(get_db)):
    """Delete document - mirrors Go's DocsHandler.Delete."""
    import os
    from ...core.config import IMAGE_STORAGE_DIR

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        logger.warning(f"[DeleteDoc] Document {doc_id} not found in DB, cleaning up vectors anyway")
    else:
        db.delete(doc)
        db.commit()

    for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink()

    try:
        request.app.state.components.vector_store.delete_by_doc_id(doc_id)
    except Exception as e:
        logger.warning(f"[DeleteDoc] Vector cleanup failed for {doc_id}: {e}")

    try:
        request.app.state.components.vector_store.delete_image_chunks_by_doc_id(doc_id)
    except Exception as e:
        logger.warning(f"[DeleteDoc] Image chunk cleanup failed for {doc_id}: {e}")

    image_dir = os.path.join(IMAGE_STORAGE_DIR, doc_id)
    if os.path.exists(image_dir):
        try:
            import shutil
            shutil.rmtree(image_dir)
            logger.info(f"[DeleteDoc] Removed image directory: {image_dir}")
        except Exception as e:
            logger.warning(f"[DeleteDoc] Image directory cleanup failed for {doc_id}: {e}")

    return {"status": "ok"}
