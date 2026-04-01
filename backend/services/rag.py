"""
RAG Pipeline Service
--------------------
Uses OpenAI for both:
  1. Embeddings       (text-embedding-3-small)
  2. Answer generation (gpt-4o-mini)

Flow:
  Embed query → retrieve top-k chunks from ChromaDB
              → build a grounded prompt
              → call OpenAI for the final answer
              → return answer + retrieved chunks (transparency)
"""

import os
import logging
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
GENERATION_MODEL = "gpt-4o-mini"

_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set in environment variables.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed_text(text: str) -> List[float]:
    """Embed a single query string using OpenAI text-embedding-3-small."""
    logger.debug("Embedding query (%d chars) with %s", len(text), EMBEDDING_MODEL)
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed_documents(texts: List[str]) -> List[List[float]]:
    """Batch embed document chunks using OpenAI (single API call)."""
    logger.info("Embedding %d chunks with %s", len(texts), EMBEDDING_MODEL)
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    logger.debug("Embedding complete: %d vectors returned", len(response.data))
    return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------

def build_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Construct a grounded RAG prompt.
    The model is explicitly instructed to answer ONLY from the provided context.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        page_info = (
            f"Page {meta['page_number']}" if meta.get("page_number", -1) != -1 else "N/A"
        )
        context_parts.append(
            f"[Source {i}] File: {meta['filename']} | {page_info}\n{chunk['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a precise legal document assistant. Your job is to answer questions strictly based on the provided document excerpts below.

RULES:
- Answer ONLY using the information in the context below.
- If the answer is not found in the context, say: "The provided documents do not contain information to answer this question."
- Quote or reference the source (filename and page) when possible.
- Be concise and accurate.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""
    return prompt


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_answer(question: str, chunks: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Generate a grounded answer given retrieved chunks using OpenAI.
    Returns (answer_text, model_name).
    """
    if not chunks:
        logger.warning("generate_answer called with no chunks — returning fallback message")
        return (
            "No documents have been uploaded yet. Please upload documents before asking questions.",
            GENERATION_MODEL,
        )

    logger.info("Generating answer with %s using %d chunks", GENERATION_MODEL, len(chunks))
    prompt = build_prompt(question, chunks)
    client = _get_openai_client()

    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()
    logger.debug("Generation complete: %d chars, finish_reason=%s",
                 len(answer), response.choices[0].finish_reason)
    return answer, GENERATION_MODEL