# AI Knowledge Indexing System

A RAG-powered document Q&A system built for legal document retrieval.
Upload PDFs, Word docs, CSVs, and plain text — then ask natural language questions grounded strictly in those documents.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| Vector Store | ChromaDB (cosine similarity) |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Render (free tier) |

## Project Structure

```
ai-knowledge-indexer/
├── backend/
│   ├── main.py                      # FastAPI app + request logging middleware
│   ├── schemas.py                   # Pydantic models
│   ├── logger.py                    # Centralised logging config
│   ├── routers/
│   │   ├── documents.py             # Upload / list / delete
│   │   └── query.py                 # Q&A endpoint
│   ├── services/
│   │   ├── document_processor.py    # Extract + chunk text
│   │   ├── vector_store.py          # ChromaDB wrapper
│   │   └── rag.py                   # Embed + generate answers (OpenAI)
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/
│       │   └── client.js            # Axios API client
│       ├── components/
│       │   ├── UploadPanel.jsx
│       │   ├── DocumentList.jsx
│       │   ├── ChatBox.jsx
│       │   └── SourceViewer.jsx
│       └── App.jsx
├── .gitignore
├── render.yaml
└── README.md
```

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENAI_API_KEY=your_key_here

uvicorn main:app --reload
# API running at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# UI running at http://localhost:5173
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload and index a document |
| `GET` | `/api/documents` | List all indexed documents |
| `DELETE` | `/api/documents/{id}` | Remove a document |
| `POST` | `/api/query` | Ask a question |
| `GET` | `/health` | Health check |

### Query request example

```json
POST /api/query
{
  "question": "What were the damages claimed in the Smith case?",
  "top_k": 5
}
```

### Query response example

```json
{
  "question": "What were the damages claimed in the Smith case?",
  "answer": "According to case_notes.pdf (Page 3), the damages claimed were $2.4M...",
  "retrieved_chunks": [
    {
      "chunk_id": "abc123_2",
      "filename": "case_notes.pdf",
      "page_number": 3,
      "content": "...The plaintiff claims damages of $2.4 million...",
      "similarity_score": 0.91
    }
  ],
  "model_used": "gpt-4o-mini"
}
```

## Deployment on Render

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/ai-knowledge-indexer.git
git push -u origin main
```

### Step 2 — Deploy Backend

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repo
3. Set **Root Directory** to `backend`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add **Environment Variables**:
   - `OPENAI_API_KEY` = your key
   - `CHROMA_PERSIST_DIR` = `/opt/render/project/chroma_db`
   - `UPLOAD_DIR` = `/opt/render/project/uploads`
   - `LOG_LEVEL` = `INFO`
7. Under **Disks**, add a disk mounted at `/opt/render/project` (1 GB)
8. Deploy → copy the service URL (e.g. `https://ai-knowledge-indexer-api.onrender.com`)
9. Add `ALLOWED_ORIGINS` = your frontend URL (fill in after Step 3)

### Step 3 — Deploy Frontend

1. Go to **New → Static Site**
2. Connect the same repo
3. Set **Root Directory** to `frontend`
4. Set **Build Command**: `npm install && npm run build`
5. Set **Publish Directory**: `dist`
6. Add **Environment Variable**:
   - `VITE_API_URL` = your backend URL from Step 2
7. Deploy

### Step 4 — Link them
Update the backend's `ALLOWED_ORIGINS` env var with your frontend URL and redeploy.

## How RAG Works (for the write-up)

```
Upload flow:
  File → Extract text (PyMuPDF / python-docx / pandas)
       → Split into ~500-char overlapping chunks
       → Embed each chunk in one batch call (OpenAI text-embedding-3-small)
       → Store in ChromaDB with metadata (filename, page, chunk index)

Query flow:
  Question → Embed (OpenAI text-embedding-3-small)
           → Cosine similarity search in ChromaDB → top-5 chunks
           → Build grounded prompt with context
           → gpt-4o-mini generates answer at temperature=0.2
           → Return answer + all retrieved chunks (transparency)
```