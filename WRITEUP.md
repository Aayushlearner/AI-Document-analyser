# AI Knowledge Indexing System — Submission Write-Up

## System Design & Approach

The system is a **Retrieval-Augmented Generation (RAG) pipeline** split into two services:

- **FastAPI backend** handles document ingestion, embedding, storage, and answer generation
- **React frontend** provides a clean interface for uploading documents and conducting Q&A

The architecture was intentionally kept modular: document processing, vector storage, and LLM interaction are each isolated services so they can be swapped independently.

---

## How Retrieval Works

**Indexing (upload time):**

1. **Extract** — Text is pulled from uploaded files using PyMuPDF (PDF), python-docx (DOCX), or pandas (CSV/XLSX). Each extractor returns `(page_number, text)` pairs so page-level provenance is preserved.
2. **Chunk** — Text is split into ~500-character overlapping windows (80-char overlap) with soft sentence-boundary detection. Smaller chunks improve retrieval precision; overlap prevents context from being cut mid-sentence.
3. **Embed** — All chunks are embedded in a single batched API call using OpenAI `text-embedding-3-small` (1536-dim), which is more efficient than sequential per-chunk calls.
4. **Store** — Embeddings and metadata (filename, page number, chunk index, document ID) are persisted in ChromaDB using cosine similarity space.

**Querying (ask time):**

1. The question is embedded using OpenAI `text-embedding-3-small`.
2. ChromaDB returns the top-5 most similar chunks by cosine similarity.
3. A grounded prompt is constructed with all 5 chunks as explicit context, with strict instructions to answer only from those sources.
4. `gpt-4o-mini` generates the final answer at temperature=0.2 (low, for factual accuracy).
5. The API response includes both the answer and all retrieved chunks with similarity scores, giving full transparency into how the answer was formed.

---

## Key Decisions

| Decision | Rationale |
|---|---|
| **OpenAI text-embedding-3-small** | 1536-dim embeddings, strong retrieval quality, supports batched input in a single API call |
| **gpt-4o-mini** | Cost-effective, fast, instruction-following — ideal for grounded RAG where hallucination is controlled by the prompt |
| **Single-batch embedding** | OpenAI accepts a list of texts in one call; avoids N sequential requests during document indexing |
| **ChromaDB** | Zero-infra vector store, persists to disk, cosine similarity built-in |
| **~500-char chunks** | Balances retrieval precision vs. context richness for 20–30 page legal docs |
| **Page-level metadata** | Enables source attribution ("Page 3 of case_notes.pdf") in every answer |
| **Temperature=0.2** | Reduces hallucination; the model stays close to the retrieved context |
| **Structured logging** | Every request, embedding call, chunk count, and generation is logged with timing for easy debugging |

---

## Challenges Faced

- **ChromaDB on Render free tier** — The free tier has an ephemeral filesystem by default. Solved by attaching a persistent disk mount and pointing `CHROMA_PERSIST_DIR` to it.
- **Embedding dimension mismatch** — Switching from Gemini (768-dim) to OpenAI (1536-dim) embeddings requires clearing the ChromaDB collection, as mixing dimensions in one collection causes query failures. Documented clearly for anyone migrating.
- **OpenAI rate limits** — Added `tenacity` retry logic with exponential backoff to handle transient `RateLimitError` and `APITimeoutError` during embedding and generation.
- **Tabular data (CSV/XLSX)** — Raw cell values are meaningless without column context. Solved by converting each row to `"Column: Value | Column: Value"` format so the LLM can read them naturally.

---

## What I Would Improve Next

1. **Smarter chunking** — Use semantic sentence embeddings to find natural paragraph breaks rather than character-count windows. Libraries like `semantic-text-splitter` or LangChain's `RecursiveCharacterTextSplitter` would help here.
2. **Re-ranking** — Apply a cross-encoder re-ranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) on the top-20 retrieved chunks before passing the top-5 to the LLM. Significantly improves answer quality.
3. **Conversation history** — Pass prior turns to the LLM so follow-up questions ("What about the next case?") resolve correctly.
4. **Hybrid search** — Combine vector similarity with BM25 keyword search (sparse + dense) for better recall on exact legal terms and case numbers.
5. **Document versioning** — Allow re-uploading an updated version of a file without manually deleting the old one.