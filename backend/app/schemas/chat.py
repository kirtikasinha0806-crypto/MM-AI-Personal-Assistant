from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    source_type: str = Field(..., description="'rag' or 'web'")
    title: str
    url: Optional[str] = None
    snippet: str
    page: Optional[int] = None


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, description="User prompt text")
    mode: Optional[str] = Field("standard", description="'standard' or 'emotional_support'")
    enable_web_search: Optional[bool] = Field(False, description="Enable Tavily live web retrieval")
    document_id: Optional[str] = Field(None, description="Optional document ID for RAG target")


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    mode: str
    sources: List[Citation] = []
    media_metadata: Optional[Dict[str, Any]] = None


class MessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    media_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ConversationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0


class ConversationDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageSchema] = []

