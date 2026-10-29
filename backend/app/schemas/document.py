from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.chat import Citation


class DocumentChunkSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    metadata_json: Optional[Dict[str, Any]] = None


class DocumentRevisionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    revision_number: int
    content: str
    change_summary: str
    created_at: datetime


class DocumentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime
    chunk_count: Optional[int] = 0


class DocumentDetailSchema(DocumentSchema):
    model_config = ConfigDict(from_attributes=True)

    content: str
    metadata_json: Optional[Dict[str, Any]] = None
    revisions: List[DocumentRevisionSchema] = []


class DocumentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the document to create")
    prompt: str = Field(..., min_length=5, description="Prompt describing what content to generate")
    file_type: Optional[str] = Field("md", description="'md' or 'txt'")


class DocumentUpdateRequest(BaseModel):
    instructions: Optional[str] = Field(None, description="Prompt instructing Gemini how to revise the document")
    direct_content: Optional[str] = Field(None, description="Direct replacement text if edited manually")


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(3, ge=1, le=10)


class RAGQueryResponse(BaseModel):
    document_id: str
    query: str
    answer: str
    citations: List[Citation] = []

