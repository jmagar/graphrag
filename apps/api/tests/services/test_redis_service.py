"""
Tests for Redis service.

Following TDD principles - tests written first to drive implementation.
"""

import pytest
import pytest_asyncio
from app.services.redis_service import RedisService


class TestRedisService:
    """Test suite for RedisService."""

    @pytest_asyncio.fixture
    async def redis_service(self):
        """Fixture providing RedisService instance."""
        service = RedisService()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_mark_page_processed(self, redis_service):
        """Test marking a page as processed."""
        crawl_id = "test-crawl-123"
        source_url = "https://example.com/page1"

        result = await redis_service.mark_page_processed(crawl_id, source_url)
        
        # Should succeed if Redis is available
        if await redis_service.is_available():
            assert result is True
        else:
            assert result is False

    @pytest.mark.asyncio
    async def test_is_page_processed_returns_true_for_marked_page(self, redis_service):
        """Test checking if a marked page is processed."""
        crawl_id = "test-crawl-456"
        source_url = "https://example.com/page2"

        # Mark the page first
        await redis_service.mark_page_processed(crawl_id, source_url)

        # Check if it's processed
        is_processed = await redis_service.is_page_processed(crawl_id, source_url)
        
        if await redis_service.is_available():
            assert is_processed is True
        else:
            assert is_processed is False

    @pytest.mark.asyncio
    async def test_is_page_processed_returns_false_for_unmarked_page(self, redis_service):
        """Test checking if an unmarked page is processed."""
        crawl_id = "test-crawl-789"
        source_url = "https://example.com/page3"

        # Don't mark the page
        is_processed = await redis_service.is_page_processed(crawl_id, source_url)
        
        # Should always return False (page not marked)
        assert is_processed is False

    @pytest.mark.asyncio
    async def test_get_processed_count(self, redis_service):
        """Test getting count of processed pages."""
        crawl_id = "test-crawl-count"
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        # Mark multiple pages
        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        count = await redis_service.get_processed_count(crawl_id)
        
        if await redis_service.is_available():
            assert count == len(urls)
        else:
            assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking(self, redis_service):
        """Test cleanup of crawl tracking data."""
        crawl_id = "test-crawl-cleanup"
        source_url = "https://example.com/page4"

        # Mark a page
        await redis_service.mark_page_processed(crawl_id, source_url)

        # Cleanup
        result = await redis_service.cleanup_crawl_tracking(crawl_id)

        if await redis_service.is_available():
            assert result is True
            
            # Verify page is no longer marked
            is_processed = await redis_service.is_page_processed(crawl_id, source_url)
            assert is_processed is False
        else:
            assert result is False

    @pytest.mark.asyncio
    async def test_cache_query_embedding(self, redis_service):
        """Test caching a query embedding."""
        query = "test search query"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        result = await redis_service.cache_query_embedding(query, embedding)
        
        if await redis_service.is_available():
            assert result is True
        else:
            assert result is False

    @pytest.mark.asyncio
    async def test_get_cached_embedding(self, redis_service):
        """Test retrieving a cached embedding."""
        query = "another test query"
        embedding = [0.6, 0.7, 0.8, 0.9, 1.0]

        # Cache the embedding
        await redis_service.cache_query_embedding(query, embedding)

        # Retrieve it
        cached = await redis_service.get_cached_embedding(query)
        
        if await redis_service.is_available():
            assert cached == embedding
        else:
            assert cached is None

    @pytest.mark.asyncio
    async def test_get_cached_embedding_returns_none_for_uncached_query(
        self, redis_service
    ):
        """Test retrieving embedding for uncached query."""
        query = "uncached query"

        cached = await redis_service.get_cached_embedding(query)
        
        # Should always return None (not cached)
        assert cached is None

    @pytest.mark.asyncio
    async def test_different_crawls_have_separate_tracking(self, redis_service):
        """Test that different crawl IDs maintain separate tracking."""
        url = "https://example.com/shared-page"
        crawl_id_1 = "crawl-1"
        crawl_id_2 = "crawl-2"

        # Mark page for crawl 1
        await redis_service.mark_page_processed(crawl_id_1, url)

        # Check both crawls
        is_processed_1 = await redis_service.is_page_processed(crawl_id_1, url)
        is_processed_2 = await redis_service.is_page_processed(crawl_id_2, url)

        if await redis_service.is_available():
            assert is_processed_1 is True
            assert is_processed_2 is False  # Not marked for crawl 2
        else:
            assert is_processed_1 is False
            assert is_processed_2 is False

    @pytest.mark.asyncio
    async def test_handles_redis_unavailable_gracefully(self):
        """Test graceful handling when Redis is unavailable."""
        # Create service (may or may not connect to Redis)
        service = RedisService()

        # All operations should return safe defaults
        result = await service.mark_page_processed("test", "https://example.com")
        assert isinstance(result, bool)

        is_processed = await service.is_page_processed("test", "https://example.com")
        assert is_processed is False  # Safe default

        count = await service.get_processed_count("test")
        assert count == 0  # Safe default

        await service.close()
