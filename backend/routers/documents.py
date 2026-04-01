"""
Documents Router
----------------
POST  /api/documents/upload   — upload a file, process, index it
GET   /api/documents           — list all indexed documents
DELETE /api/documents/{doc_id} — remove a document from the index
"""

import os
import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from schemas import DocumentMeta, DocumentListResponse, UploadResponse
from services.document_processor import extract_and_chunk, get_page_count
from services.rag import embed_documents
from services import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
METADATA_FILE = os.path.join(UPLOAD_DIR, "_metadata.json")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}
MAX_FILE_SIZE_MB = 20


# ---------------------------------------------------------------------------
# Helpers — persistent metadata store (simple JSON file)
# ---------------------------------------------------------------------------

def _load_metadata() -> dict:
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_metadata(meta: dict):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(meta, f, indent=2)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    logger.info("Upload started: filename='%s'", file.filename)

    # --- Validate extension ---
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("Rejected upload '%s': unsupported extension '%s'", file.filename, ext)
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # --- Read & size-check ---
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        logger.warning("Rejected upload '%s': file too large (%.1f MB)", file.filename, size_mb)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max allowed: {MAX_FILE_SIZE_MB} MB.",
        )
    logger.debug("File size: %.2f MB", size_mb)

    # --- Save to disk ---
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    document_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{document_id}{ext}")
    with open(saved_path, "wb") as f:
        f.write(content)
    logger.debug("Saved to disk: %s", saved_path)

    # --- Process: extract text → chunk ---
    try:
        chunks = extract_and_chunk(saved_path, file.filename)
    except Exception as e:
        os.remove(saved_path)
        logger.error("Text extraction failed for '%s': %s", file.filename, e, exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process document: {str(e)}")

    if not chunks:
        os.remove(saved_path)
        logger.warning("No extractable text in '%s'", file.filename)
        raise HTTPException(status_code=422, detail="No extractable text found in the document.")

    logger.info("Extracted %d chunks from '%s'", len(chunks), file.filename)

    # --- Embed chunks ---
    try:
        texts = [c["content"] for c in chunks]
        embeddings = embed_documents(texts)
    except Exception as e:
        os.remove(saved_path)
        logger.error("Embedding failed for '%s': %s", file.filename, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Embedding failed: {str(e)}")

    logger.debug("Embeddings generated: %d vectors", len(embeddings))

    # --- Store in ChromaDB ---
    try:
        vector_store.add_chunks(document_id, chunks, embeddings)
    except Exception as e:
        os.remove(saved_path)
        logger.error("Vector store insertion failed for '%s': %s", file.filename, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Vector store error: {str(e)}")

    logger.debug("Chunks stored in ChromaDB for document_id=%s", document_id)

    # --- Persist metadata ---
    page_count = get_page_count(saved_path, file.filename)
    doc_meta = DocumentMeta(
        id=document_id,
        filename=file.filename,
        file_type=ext.lstrip("."),
        page_count=page_count,
        chunk_count=len(chunks),
        uploaded_at=datetime.now(timezone.utc).isoformat(),
    )
    all_meta = _load_metadata()
    all_meta[document_id] = doc_meta.model_dump()
    _save_metadata(all_meta)

    logger.info(
        "Upload complete: '%s' | id=%s | pages=%d | chunks=%d",
        file.filename, document_id, page_count, len(chunks),
    )
    return UploadResponse(
        success=True,
        document=doc_meta,
        message=f"Successfully indexed {len(chunks)} chunks from '{file.filename}'.",
    )


@router.get("", response_model=DocumentListResponse)
def list_documents():
    all_meta = _load_metadata()
    docs = [DocumentMeta(**v) for v in all_meta.values()]
    docs.sort(key=lambda d: d.uploaded_at, reverse=True)
    logger.debug("Listed %d documents", len(docs))
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(document_id: str):
    all_meta = _load_metadata()
    if document_id not in all_meta:
        logger.warning("Delete failed: document_id=%s not found", document_id)
        raise HTTPException(status_code=404, detail="Document not found.")

    doc = all_meta[document_id]
    logger.info("Deleting document: '%s' (id=%s)", doc["filename"], document_id)

    vector_store.delete_document(document_id)

    ext = f".{doc['file_type']}"
    saved_path = os.path.join(UPLOAD_DIR, f"{document_id}{ext}")
    if os.path.exists(saved_path):
        os.remove(saved_path)

    del all_meta[document_id]
    _save_metadata(all_meta)

    logger.info("Deleted document: '%s'", doc["filename"])
    return {"success": True, "message": f"Document '{doc['filename']}' deleted."}