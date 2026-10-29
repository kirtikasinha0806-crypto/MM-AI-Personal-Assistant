import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.session import init_db, engine, is_using_fallback
from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.api.search import router as search_router
from backend.app.services.llm_service import llm_service
from backend.app.services.search_service import search_service

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("multimodal-assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initializes database and checks services on startup."""
    logger.info("Initializing Multimodal Assistant backend services...")
    db_ok = init_db()
    if db_ok:
        logger.info("Database schemas and extensions initialized.")
    else:
        logger.warning("Database initialization had warnings/errors. Proceeding with caution.")
    yield
    logger.info("Shutting down backend services...")


app = FastAPI(
    title="Multimodal AI Personal Assistant API",
    description="Backend API for Multimodal Chat, RAG, Web Search, and Document Management.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Streamlit or browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(search_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health status endpoint reporting DB connection and external API readiness."""
    from backend.app.db.session import is_using_fallback
    db_healthy = False
    db_type = "unknown"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_healthy = True
        db_type = "sqlite_fallback" if is_using_fallback() else "postgresql"
    except Exception:
        db_healthy = False

    return {
        "status": "ok",
        "database_connected": db_healthy,
        "database_type": db_type,
        "database_url": str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url),
        "gemini_configured": llm_service.is_configured(),
        "gemini_model": settings.GEMINI_MODEL,
        "tavily_configured": search_service.is_configured(),
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
