"""
Pytest configuration and shared fixtures for GraphRAG API tests.

This module provides:
- Mock service fixtures (Firecrawl, Embeddings, VectorDB, LLM)
- Test client fixtures
- Sample data fixtures
- Environment configuration for tests
- Database fixtures for testing
"""
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
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
    service.search = AsyncMock(return_value=[
        {
            "id": "doc1",
            "score": 0.95,
            "payload": {
                "content": "Sample content",
                "metadata": {"sourceURL": "https://example.com"}
            }
        }
    ])
    service.get_collection_info = AsyncMock(return_value={
        "name": "graphrag",
        "points_count": 100,
        "vectors_count": 100,
        "status": "green"
    })
    return service


@pytest.fixture
def mock_firecrawl_service():
    """
    Mock FirecrawlService with pre-configured responses.
    
    Returns:
        Mock object with start_crawl, get_crawl_status, and cancel_crawl methods
    """
    service = MagicMock()
    service.start_crawl = AsyncMock(return_value={
        "id": "crawl_123",
        "status": "started",
        "url": "https://example.com"
    })
    service.get_crawl_status = AsyncMock(return_value={
        "id": "crawl_123",
        "status": "completed",
        "total": 5,
        "completed": 5,
        "data": []
    })
    service.cancel_crawl = AsyncMock(return_value={
        "id": "crawl_123",
        "status": "cancelled"
    })
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
            "statusCode": 200
        },
        "links": ["https://example.com/page2"]
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
                "description": "This is an example page"
            }
        }
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
                "metadata": {"sourceURL": "https://example.com/page1", "title": "Page 1"}
            },
            {
                "markdown": "# Page 2",
                "metadata": {"sourceURL": "https://example.com/page2", "title": "Page 2"}
            }
        ]
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
        "error": "Failed to crawl: Connection timeout"
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
        "maxPages": 10
    }


@pytest.fixture
def sample_query_request() -> Dict[str, Any]:
    """
    Sample query request payload.
    
    Returns:
        Dictionary matching QueryRequest schema
    """
    return {
        "query": "What is GraphRAG?",
        "limit": 5,
        "use_llm": True
    }


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
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
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
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()
