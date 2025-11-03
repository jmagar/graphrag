"""
Pytest configuration and shared fixtures for GraphRAG API tests.

This module provides:
- Mock service fixtures (Firecrawl, Embeddings, VectorDB, LLM)
- Test client fixtures
- Sample data fixtures
- Environment configuration for tests
- Database fixtures for testing
"""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set required environment variables before importing app modules
os.environ.setdefault("FIRECRAWL_URL", "http://mock-firecrawl:4200")
os.environ.setdefault("FIRECRAWL_API_KEY", "test-api-key")
os.environ.setdefault("DEBUG", "true")  # Allow tests to run without webhook secret
os.environ.setdefault("QDRANT_URL", "http://mock-qdrant:6333")
os.environ.setdefault("TEI_URL", "http://mock-tei:8080")
os.environ.setdefault("OLLAMA_URL", "http://mock-ollama:11434")
os.environ.setdefault("WEBHOOK_BASE_URL", "http://test:4400")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

# Mock service initialization to prevent actual connections during imports
# Note: VectorDBService now uses AsyncQdrantClient and requires initialize() call
with patch("app.services.embeddings.httpx.AsyncClient"):
    from app.main import app
    from app.db.models import Base


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


# Configure anyio for all async fixtures
pytest_plugins = ("anyio",)


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an httpx AsyncClient for testing FastAPI endpoints.

    Usage:
        async def test_endpoint(test_client):
            response = await test_client.get("/api/v1/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_embeddings_service():
    """
    Mock EmbeddingsService with pre-configured responses.

    Returns:
        Mock object with generate_embedding method
    """
    service = MagicMock()
    # Return a 768-dimensional embedding (matches TEI output)
    service.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return service


@pytest.fixture
def mock_vector_db_service():
    """
    Mock VectorDBService with pre-configured responses.

    Returns:
        Mock object with upsert_document, search, and get_collection_info methods
    """
    service = MagicMock()
    service.upsert_document = AsyncMock(return_value=None)
    service.search = AsyncMock(
        return_value=[
            {
                "id": "doc1",
                "score": 0.95,
                "content": "Sample content",
                "metadata": {"sourceURL": "https://example.com"},
            }
        ]
    )
    service.get_collection_info = AsyncMock(
        return_value={
            "name": "graphrag",
            "points_count": 100,
            "vectors_count": 100,
            "status": "green",
        }
    )
    return service


@pytest.fixture
def mock_firecrawl_service():
    """
    Mock FirecrawlService with pre-configured responses.

    Returns:
        Mock object with start_crawl, get_crawl_status, and cancel_crawl methods
    """
    service = MagicMock()
    service.start_crawl = AsyncMock(
        return_value={"id": "crawl_123", "status": "started", "url": "https://example.com"}
    )
    service.get_crawl_status = AsyncMock(
        return_value={
            "id": "crawl_123",
            "status": "completed",
            "total": 5,
            "completed": 5,
            "data": [],
        }
    )
    service.cancel_crawl = AsyncMock(return_value={"id": "crawl_123", "status": "cancelled"})
    return service


@pytest.fixture
def mock_llm_service():
    """
    Mock LLMService with pre-configured responses.

    Returns:
        Mock object with generate_response method
    """
    service = MagicMock()
    service.generate_response = AsyncMock(return_value="This is a test response from the LLM.")
    return service


@pytest.fixture
def mock_redis_service():
    """
    Mock RedisService with pre-configured responses.

    Returns:
        Mock object with async Redis operations
    """
    service = MagicMock()
    service.is_duplicate = AsyncMock(return_value=False)
    service.mark_as_processed = AsyncMock(return_value=None)
    service.get_crawl_status = AsyncMock(return_value=None)
    service.update_crawl_status = AsyncMock(return_value=None)
    # Add methods used by webhooks
    service.mark_page_processed = AsyncMock(return_value=True)
    service.is_page_processed = AsyncMock(return_value=False)
    service.cleanup_crawl_tracking = AsyncMock(return_value=True)
    service.get_processed_count = AsyncMock(return_value=0)
    return service


@pytest.fixture
def mock_language_detection_service():
    """
    Mock LanguageDetectionService with pre-configured responses.

    Returns:
        Mock object with language detection methods
    """
    service = MagicMock()
    service.detect = AsyncMock(return_value="en")
    service.is_supported = AsyncMock(return_value=True)
    # The webhook code calls detect_language (sync method)
    service.detect_language = MagicMock(return_value="en")
    return service


@pytest.fixture
def mock_graph_db_service():
    """
    Mock GraphDBService with pre-configured responses.

    Returns:
        Mock object with entity and relationship methods
    """
    service = MagicMock()
    service.get_entity_by_id = AsyncMock(return_value=None)
    service.find_connected_entities = AsyncMock(return_value=[])
    service.search_entities = AsyncMock(return_value=[])
    service.create_entity = AsyncMock(return_value=None)
    service.create_relationship = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_entity_extractor():
    """
    Mock EntityExtractor with pre-configured responses.

    Returns:
        Mock object with extract_entities method
    """
    service = MagicMock()
    service.extract_entities = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_relationship_extractor():
    """
    Mock RelationshipExtractor with pre-configured responses.

    Returns:
        Mock object with extract_relationships method
    """
    service = MagicMock()
    service.extract_relationships = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_hybrid_query_engine():
    """
    Mock HybridQueryEngine with pre-configured responses.

    Returns:
        Mock object with hybrid_search method
    """
    service = MagicMock()
    service.hybrid_search = AsyncMock(
        return_value={
            "query": "",
            "query_entities": [],
            "vector_results": [],
            "graph_results": [],
            "combined_results": [],
            "retrieval_strategy": "vector"
        }
    )
    return service


@pytest.fixture
def sample_crawl_page_data() -> Dict[str, Any]:
    """
    Sample page data as received from Firecrawl webhook (crawl.page event).

    Returns:
        Dictionary matching Firecrawl v2 page data structure
    """
    return {
        "markdown": "# Example Page\n\nThis is sample content from a crawled page.",
        "html": "<html><body><h1>Example Page</h1><p>This is sample content.</p></body></html>",
        "metadata": {
            "sourceURL": "https://example.com/page1",
            "title": "Example Page",
            "description": "This is an example page",
            "language": "en",
            "statusCode": 200,
        },
        "links": ["https://example.com/page2"],
    }


@pytest.fixture
def sample_webhook_crawl_page() -> Dict[str, Any]:
    """
    Sample webhook payload for crawl.page event.

    Returns:
        Complete webhook payload as sent by Firecrawl
    """
    return {
        "type": "crawl.page",
        "id": "crawl_123",
        "data": {
            "markdown": "# Example Page\n\nThis is sample content from a crawled page.",
            "metadata": {
                "sourceURL": "https://example.com/page1",
                "title": "Example Page",
                "description": "This is an example page",
                "statusCode": 200,
            },
        },
    }


@pytest.fixture
def sample_webhook_crawl_completed() -> Dict[str, Any]:
    """
    Sample webhook payload for crawl.completed event.

    Returns:
        Complete webhook payload as sent by Firecrawl
    """
    return {
        "type": "crawl.completed",
        "id": "crawl_123",
        "data": [
            {
                "markdown": "# Page 1",
                "metadata": {"sourceURL": "https://example.com/page1", "title": "Page 1", "statusCode": 200},
            },
            {
                "markdown": "# Page 2",
                "metadata": {"sourceURL": "https://example.com/page2", "title": "Page 2", "statusCode": 200},
            },
        ],
    }


@pytest.fixture
def sample_webhook_crawl_failed() -> Dict[str, Any]:
    """
    Sample webhook payload for crawl.failed event.

    Returns:
        Complete webhook payload as sent by Firecrawl
    """
    return {
        "type": "crawl.failed",
        "id": "crawl_123",
        "error": "Failed to crawl: Connection timeout",
    }


@pytest.fixture
def sample_crawl_request() -> Dict[str, Any]:
    """
    Sample crawl request payload.

    Returns:
        Dictionary matching CrawlRequest schema
    """
    return {
        "url": "https://example.com",
        "includes": ["**/docs/**"],
        "excludes": ["**/admin/**"],
        "maxDepth": 3,
        "maxPages": 10,
    }


@pytest.fixture
def sample_query_request() -> Dict[str, Any]:
    """
    Sample query request payload.

    Returns:
        Dictionary matching QueryRequest schema
    """
    return {"query": "What is GraphRAG?", "limit": 5, "use_llm": True}


@pytest.fixture
def mock_settings(monkeypatch):
    """
    Mock application settings for testing.

    Usage:
        def test_with_mock_settings(mock_settings):
            assert settings.FIRECRAWL_URL == "http://mock-firecrawl:4200"
    """
    monkeypatch.setenv("FIRECRAWL_URL", "http://mock-firecrawl:4200")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-api-key")
    monkeypatch.setenv("QDRANT_URL", "http://mock-qdrant:6333")
    monkeypatch.setenv("TEI_URL", "http://mock-tei:8080")
    monkeypatch.setenv("OLLAMA_URL", "http://mock-ollama:11434")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "http://test:4400")


@pytest.fixture(autouse=True)
def disable_webhook_signature_verification(monkeypatch):
    """
    Automatically disable webhook signature verification for all tests by default.

    This fixture runs automatically for all tests (autouse=True) and ensures
    that webhook endpoints don't require signatures unless explicitly testing
    signature verification.

    Tests that need to test signature verification should use the
    'setup_webhook_secret' fixture from test_webhook_e2e.py which will
    override this by setting the secret after this fixture runs.

    This prevents 401 Unauthorized errors in tests that aren't focused on
    signature verification functionality.
    """
    # Set webhook secret to empty string to disable signature verification
    # (delenv doesn't work because Settings reads from .env file)
    monkeypatch.setenv("FIRECRAWL_WEBHOOK_SECRET", "")

    # Force reload settings to pick up the empty secret
    from app.core import config
    config.settings = config.Settings()

    # Also patch settings in webhook module since it's already imported
    from app.api.v1.endpoints import webhooks
    monkeypatch.setattr(webhooks, "settings", config.settings)


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")
async def db_engine(anyio_backend):
    """
    Create a test database engine using SQLite in-memory.

    Each test function gets a fresh database.
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session for testing.

    Each test gets a fresh session that's rolled back after the test.

    Usage:
        async def test_something(db_session):
            obj = MyModel(name="test")
            db_session.add(obj)
            await db_session.commit()
    """
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()
