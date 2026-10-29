import logging
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from backend.app.core.config import settings
from backend.app.schemas.search import SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Service wrapper for Tavily Search API."""

    def __init__(self):
        self._client: Optional[TavilyClient] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if settings.is_tavily_configured:
            try:
                self._client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                logger.info("Tavily search client successfully initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {e}")
                self._client = None
        else:
            self._client = None

    def is_configured(self) -> bool:
        return self._client is not None

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Performs a live web search using Tavily.

        Returns a list of SearchResult items with verified title, url, and snippet.
        """
        if not self.is_configured():
            logger.warning("Tavily search invoked but TAVILY_API_KEY is not configured.")
            return []

        try:
            response = self._client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=False,
            )

            raw_results = response.get("results", [])
            results: List[SearchResult] = []
            for item in raw_results:
                title = item.get("title", "Untitled Web Result")
                url = item.get("url", "")
                snippet = item.get("content", "")
                if snippet:
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet[:400]
                    ))
            return results

        except Exception as e:
            logger.error(f"Tavily search execution failed for query '{query}': {e}", exc_info=True)
            return []

    def format_results_for_prompt(self, results: List[SearchResult]) -> str:
        """Formats search results into structured plain text for Gemini's context."""
        if not results:
            return ""

        formatted_parts = []
        for idx, res in enumerate(results, 1):
            formatted_parts.append(
                f"[{idx}] Source Title: {res.title}\n"
                f"URL: {res.url}\n"
                f"Content: {res.snippet}\n"
            )
        return "\n".join(formatted_parts)


search_service = SearchService()

