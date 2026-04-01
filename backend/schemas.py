from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class DocumentMeta(BaseModel):
    id: str
    filename: str
    file_type: str
    page_count: int
    chunk_count: int
    uploaded_at: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentMeta]
    total: int


class UploadResponse(BaseModel):
    success: bool
    document: DocumentMeta
    message: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: Optional[int]
    content: str
    similarity_score: float


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: List[RetrievedChunk]
    model_used: str