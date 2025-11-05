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
from app.services.firecrawl import FirecrawlService
from app.services.vector_db import VectorDBService
from app.services.embeddings import EmbeddingsService
from app.services.llm import LLMService
from app.services.redis_service import RedisService
from app.services.query_cache import QueryCache
from app.services.language_detection import LanguageDetectionService
from app.services.graph_db import GraphDBService
from app.services.entity_extractor import EntityExtractor
from app.services.relationship_extractor import RelationshipExtractor
from app.services.hybrid_query import HybridQueryEngine
from app.dependencies import (
    set_firecrawl_service,
    set_vector_db_service,
    set_embeddings_service,
    set_llm_service,
    set_redis_service,
    set_query_cache,
    set_language_detection_service,
    set_graph_db_service,
    set_entity_extractor,
    set_relationship_extractor,
    clear_all_services,
)
from app.api.v1.endpoints.graph import set_hybrid_query_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with proper resource cleanup.
    """
    # Startup: Initialize services
    logger.info("=" * 80)
    logger.info("🚀 Starting GraphRAG API v%s", settings.VERSION)
    logger.info("=" * 80)
    
    # Log configuration summary
    logger.info("📋 Configuration Summary:")
    logger.info("  • Debug Mode: %s", "ON" if settings.DEBUG else "OFF")
    logger.info("  • Firecrawl: %s", settings.FIRECRAWL_URL)
    logger.info("  • Qdrant: %s", settings.QDRANT_URL)
    logger.info("  • TEI Embeddings: %s", settings.TEI_URL)
    logger.info("  • Neo4j: %s", settings.NEO4J_URI)
    logger.info("  • Redis: %s:%d", settings.REDIS_HOST, settings.REDIS_PORT)
    logger.info("  • Webhook URL: %s", settings.WEBHOOK_BASE_URL)
    
    # Warn about localhost webhook URL
    if "localhost" in settings.WEBHOOK_BASE_URL or "127.0.0.1" in settings.WEBHOOK_BASE_URL:
        logger.warning("=" * 80)
        logger.warning("⚠️  WARNING: Webhook URL uses localhost!")
        logger.warning("⚠️  This will NOT work if Firecrawl is on a different host.")
        logger.warning("⚠️  Current: %s", settings.WEBHOOK_BASE_URL)
        logger.warning("⚠️  Crawl operations may fail silently.")
        logger.warning("⚠️  Consider using your IP address instead (e.g., http://10.1.0.6:4400)")
        logger.warning("=" * 80)
    
    if settings.OLLAMA_URL:
        logger.info("  • Ollama: %s (model: %s)", settings.OLLAMA_URL, settings.OLLAMA_MODEL)
    logger.info("-" * 80)

    # Initialize database
    logger.info("🗄️  Initializing SQLite database...")
    await init_db()
    logger.info("✅ SQLite database initialized")

    # Initialize all service singletons
    logger.info("🔧 Initializing services...")
    
    firecrawl_service = FirecrawlService()
    set_firecrawl_service(firecrawl_service)
    logger.info("  ✅ FirecrawlService initialized")

    # Initialize Redis first (required by QueryCache)
    logger.info("🔌 Connecting to Redis at %s:%d...", settings.REDIS_HOST, settings.REDIS_PORT)
    redis_service = RedisService()
    set_redis_service(redis_service)

    # Initialize QueryCache with Redis client
    # Check if Redis is available before enabling cache
    redis_available = False
    try:
        await redis_service.client.ping()
        redis_available = True
        logger.info("  ✅ Redis connection verified")
    except Exception as e:
        logger.warning("  ⚠️  Redis unavailable: %s", e)

    query_cache = None
    if settings.ENABLE_QUERY_CACHE and redis_available:
        query_cache = QueryCache(
            redis_client=redis_service.client,
            default_ttl=settings.QUERY_CACHE_TTL,
            enabled=True,
        )
        set_query_cache(query_cache)
        logger.info("  ✅ QueryCache initialized (TTL: %ds)", settings.QUERY_CACHE_TTL)
    else:
        # Create disabled cache for dependency injection
        query_cache = QueryCache(
            redis_client=redis_service.client,
            default_ttl=settings.QUERY_CACHE_TTL,
            enabled=False,
        )
        set_query_cache(query_cache)
        if not redis_available:
            logger.warning("  ⚠️  QueryCache DISABLED - Redis unavailable")
        else:
            logger.info("  ⚠️  QueryCache DISABLED via configuration")

    # Initialize VectorDBService with QueryCache
    logger.info("🔌 Connecting to Qdrant at %s...", settings.QDRANT_URL)
    vector_db_service = VectorDBService(query_cache=query_cache)
    await vector_db_service.initialize()
    set_vector_db_service(vector_db_service)
    logger.info("  ✅ VectorDBService initialized")

    embeddings_service = EmbeddingsService()
    set_embeddings_service(embeddings_service)
    logger.info("  ✅ EmbeddingsService initialized")

    llm_service = LLMService()
    set_llm_service(llm_service)
    logger.info("  ✅ LLMService initialized")

    lang_service = LanguageDetectionService()
    set_language_detection_service(lang_service)
    logger.info("  ✅ LanguageDetectionService initialized")

    # Initialize GraphRAG services
    graph_db_service = GraphDBService()
    await graph_db_service.initialize()
    set_graph_db_service(graph_db_service)

    entity_extractor = EntityExtractor()
    set_entity_extractor(entity_extractor)
    logger.info("  ✅ EntityExtractor initialized")

    relationship_extractor = RelationshipExtractor()
    set_relationship_extractor(relationship_extractor)
    logger.info("  ✅ RelationshipExtractor initialized")

    # Initialize HybridQueryEngine with QueryCache
    hybrid_query_engine = HybridQueryEngine(query_cache=query_cache)
    await hybrid_query_engine.vector_db_service.initialize()
    set_hybrid_query_engine(hybrid_query_engine)
    logger.info("  ✅ HybridQueryEngine initialized")

    # Validate critical service configuration
    if not settings.FIRECRAWL_URL:
        logger.warning(
            "FIRECRAWL_URL not configured - scrape/map/search/extract endpoints will fail"
        )
    if not settings.QDRANT_URL:
        logger.warning("QDRANT_URL not configured - RAG features will fail")
    if not settings.TEI_URL:
        logger.warning("TEI_URL not configured - embeddings generation will fail")

    # Log language filtering configuration
    if settings.ENABLE_LANGUAGE_FILTERING:
        logger.info(
            f"🌍 Language filtering ENABLED: "
            f"allowed={settings.allowed_languages_list}, "
            f"mode={settings.LANGUAGE_FILTER_MODE}"
        )
    else:
        logger.info("🌍 Language filtering DISABLED - processing all languages")

    # Log streaming configuration
    if settings.ENABLE_STREAMING_PROCESSING:
        logger.info("⚡ Streaming processing ENABLED - pages processed immediately")
    else:
        logger.info("📦 Batch processing ENABLED - pages processed at crawl completion")

    # Log query cache configuration
    if settings.ENABLE_QUERY_CACHE:
        logger.info(f"💾 Query cache ENABLED (TTL: {settings.QUERY_CACHE_TTL}s)")
    else:
        logger.info("💾 Query cache DISABLED")

    logger.info("=" * 80)
    logger.info("✨ GraphRAG API startup complete!")
    logger.info("🌐 API listening on http://0.0.0.0:4400")
    logger.info("📖 API docs available at http://localhost:4400/api/v1/docs")
    logger.info("=" * 80)

    yield

    # Shutdown: Clean up resources
    logger.info("🛑 Shutting down GraphRAG API...")

    # Close all services
    try:
        await firecrawl_service.close()
        logger.info("✅ FirecrawlService closed")
    except Exception as e:
        logger.error(f"❌ Error closing FirecrawlService: {e}")

    try:
        await vector_db_service.close()
        logger.info("✅ VectorDBService closed")
    except Exception as e:
        logger.error(f"❌ Error closing VectorDBService: {e}")

    try:
        await embeddings_service.close()
        logger.info("✅ EmbeddingsService closed")
    except Exception as e:
        logger.error(f"❌ Error closing EmbeddingsService: {e}")

    try:
        await llm_service.close()
        logger.info("✅ LLMService closed")
    except Exception as e:
        logger.error(f"❌ Error closing LLMService: {e}")

    try:
        await redis_service.close()
        logger.info("✅ RedisService closed")
    except Exception as e:
        logger.error(f"❌ Error closing RedisService: {e}")

    try:
        await graph_db_service.close()
        logger.info("✅ GraphDBService closed")
    except Exception as e:
        logger.error(f"❌ Error closing GraphDBService: {e}")

    # Clear all service singletons
    clear_all_services()

    # Close database connections
    await close_db()

    logger.info("👋 GraphRAG API shutdown complete")


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
