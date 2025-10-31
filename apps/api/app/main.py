"""
FastAPI main application entry point.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.database import init_db, close_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    await init_db()

    # Validate critical service configuration
    if not settings.FIRECRAWL_URL:
        logger.warning(
            "FIRECRAWL_URL not configured - scrape/map/search/extract endpoints will fail"
        )
    if not settings.QDRANT_URL:
        logger.warning("QDRANT_URL not configured - RAG features will fail")
    if not settings.TEI_URL:
        logger.warning("TEI_URL not configured - embeddings generation will fail")

    yield
    # Shutdown: Close database connections
    await close_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="GraphRAG API with Firecrawl v2, Qdrant, and TEI embeddings",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "services": {
            "firecrawl": settings.FIRECRAWL_URL,
            "qdrant": settings.QDRANT_URL,
            "tei": settings.TEI_URL,
        },
    }


@app.head("/health")
async def health_check_head():
    """Lightweight health check endpoint (HEAD method)."""
    return None  # FastAPI returns 200 OK with no body for HEAD requests


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=4400,
        reload=True,
    )
