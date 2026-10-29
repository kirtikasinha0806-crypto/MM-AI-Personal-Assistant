import logging
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.search_service import search_service
from backend.app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
def execute_search(req: SearchRequest):
    """Executes a standalone Tavily web search and returns results with an optional AI synthesis."""
    if not search_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily Web Search is not configured. Please set TAVILY_API_KEY in .env."
        )

    results = search_service.search(query=req.query, max_results=req.max_results or 5)

    synthesized = None
    if results and llm_service.is_configured():
        context = search_service.format_results_for_prompt(results)
        prompt = (
            f"Please synthesize a clear, helpful answer to the question '{req.query}' using only the "
            f"following web search results:\n\n{context}"
        )
        synthesized = llm_service.generate_chat_response(prompt=prompt)

    return SearchResponse(
        query=req.query,
        results=results,
        synthesized_answer=synthesized
    )

