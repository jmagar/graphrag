"""
Application configuration using Pydantic settings.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "GraphRAG API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://10.1.0.6:3000",
        "http://10.1.0.6:3001",
    ]

    # Firecrawl v2 API
    FIRECRAWL_URL: str
    FIRECRAWL_API_KEY: str

    # Qdrant vector database
    QDRANT_URL: str
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "graphrag"

    # TEI embeddings service
    TEI_URL: str

    # Reranker service (optional)
    RERANKER_URL: str = ""

    # Ollama for LLM
    OLLAMA_URL: str = ""
    OLLAMA_MODEL: str = "qwen3:4b"

    # Webhook URL for Firecrawl callbacks
    WEBHOOK_BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./graphrag.db"
    DEBUG: bool = False


settings = Settings()
