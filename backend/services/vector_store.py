"""
Vector Store Service
--------------------
Thin wrapper around ChromaDB.

Responsibilities:
  - Persist a ChromaDB collection at CHROMA_PERSIST_DIR
  - Add chunks with embeddings and metadata
  - Query by embedding similarity
  - Delete all chunks belonging to a document
  - List distinct documents stored
"""

import os
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_client: Optional[chromadb.PersistentClient] = None
_collection = None

COLLECTION_NAME = "law_firm_docs"


def _get_collection():
    global _client, _collection
    if _collection is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        os.makedirs(persist_dir, exist_ok=True)
        logger.info("Initialising ChromaDB at '%s'", persist_dir)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' ready (%d items)", COLLECTION_NAME, _collection.count())
    return _collection


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def add_chunks(
    document_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
):
    """
    Store chunks in ChromaDB.

    Each chunk dict must have: content, page_number, chunk_index, filename
    """
    col = _get_collection()

    ids = [f"{document_id}_{c['chunk_index']}" for c in chunks]
    documents = [c["content"] for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "filename": c["filename"],
            "page_number": c["page_number"] if c["page_number"] is not None else -1,
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    col.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info("Stored %d chunks for document_id=%s", len(chunks), document_id)


def delete_document(document_id: str):
    """Remove all chunks belonging to a document."""
    col = _get_collection()
    col.delete(where={"document_id": document_id})
    logger.info("Deleted all chunks for document_id=%s", document_id)


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def query_chunks(
    query_embedding: List[float],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Return the top_k most similar chunks with their metadata and distances.
    """
    col = _get_collection()

    # Guard against querying an empty collection
    if col.count() == 0:
        return []

    results = col.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        similarity = 1 - distance  # cosine distance → similarity
        chunks.append(
            {
                "chunk_id": doc_id,
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "similarity_score": round(similarity, 4),
            }
        )

    logger.debug("Query returned %d chunks from %d total items", len(chunks), col.count())
    return chunks


def list_documents() -> List[Dict[str, Any]]:
    """
    Return distinct documents stored in ChromaDB with their chunk counts.
    Returns list of {document_id, filename, chunk_count}.
    """
    col = _get_collection()

    if col.count() == 0:
        return []

    # Fetch all metadata (no embeddings needed)
    result = col.get(include=["metadatas"])
    metadatas = result["metadatas"]

    # Aggregate by document_id
    doc_map: Dict[str, Dict] = {}
    for meta in metadatas:
        doc_id = meta["document_id"]
        if doc_id not in doc_map:
            doc_map[doc_id] = {
                "document_id": doc_id,
                "filename": meta["filename"],
                "chunk_count": 0,
            }
        doc_map[doc_id]["chunk_count"] += 1

    return list(doc_map.values())


def document_exists(document_id: str) -> bool:
    col = _get_collection()
    result = col.get(where={"document_id": document_id}, limit=1)
    return len(result["ids"]) > 0