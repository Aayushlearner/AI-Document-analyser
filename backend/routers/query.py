"""
Query Router
------------
POST /api/query  — ask a natural-language question,
                   returns answer + retrieved source chunks for transparency
"""

import logging

from fastapi import APIRouter, HTTPException

from schemas import QueryRequest, QueryResponse, RetrievedChunk
from services.rag import embed_text, generate_answer
from services import vector_store

router = APIRouter(prefix="/api/query", tags=["query"])
logger = logging.getLogger(__name__)


@router.post("", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    question_preview = request.question[:80].replace("\n", " ")
    logger.info("Query received: '%s' (top_k=%d)", question_preview, request.top_k)

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Embed the query
    try:
        query_embedding = embed_text(request.question)
    except Exception as e:
        logger.error("Query embedding failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Embedding failed: {str(e)}")

    logger.debug("Query embedded successfully")

    # 2. Retrieve top-k relevant chunks from ChromaDB
    try:
        raw_chunks = vector_store.query_chunks(
            query_embedding=query_embedding,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error("Chunk retrieval failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    logger.info(
        "Retrieved %d chunks (top score: %.3f)",
        len(raw_chunks),
        raw_chunks[0]["similarity_score"] if raw_chunks else 0.0,
    )

    # 3. Generate grounded answer
    try:
        answer, model_used = generate_answer(request.question, raw_chunks)
    except Exception as e:
        logger.error("Answer generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Generation failed: {str(e)}")

    logger.info("Answer generated via %s (%d chars)", model_used, len(answer))

    # 4. Format retrieved chunks for the response (transparency)
    retrieved_chunks = [
        RetrievedChunk(
            chunk_id=c["chunk_id"],
            document_id=c["metadata"]["document_id"],
            filename=c["metadata"]["filename"],
            page_number=(
                c["metadata"]["page_number"]
                if c["metadata"].get("page_number", -1) != -1
                else None
            ),
            content=c["content"],
            similarity_score=c["similarity_score"],
        )
        for c in raw_chunks
    ]

    return QueryResponse(
        question=request.question,
        answer=answer,
        retrieved_chunks=retrieved_chunks,
        model_used=model_used,
    )