from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.api.search import router as search_router

__all__ = [
    "chat_router",
    "documents_router",
    "search_router",
]

