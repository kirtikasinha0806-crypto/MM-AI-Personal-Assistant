from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query string for web search")
    max_results: Optional[int] = Field(5, ge=1, le=10)


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    synthesized_answer: Optional[str] = None

