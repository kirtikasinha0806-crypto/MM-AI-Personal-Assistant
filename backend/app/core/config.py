import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = "http://localhost:8000"

    # Database settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/multimodal_assistant"

    # AI Model settings (Google Gemini)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Web Search settings (Tavily)
    TAVILY_API_KEY: Optional[str] = None

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Document Chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip() and self.GEMINI_API_KEY != "your_gemini_api_key_here")

    @property
    def is_tavily_configured(self) -> bool:
        return bool(self.TAVILY_API_KEY and self.TAVILY_API_KEY.strip() and self.TAVILY_API_KEY != "your_tavily_api_key_here")


settings = Settings()

