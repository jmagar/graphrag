"""
Comprehensive tests for Redis deduplication logic.

Tests verify:
1. mark_page_processed() - key creation with TTL
2. is_page_processed() - correct existence checking
3. cleanup_crawl_tracking() - bulk key deletion
4. Streaming mode: pages marked as processed during crawl.page events
5. Batch mode: already-processed pages skipped in crawl.completed
6. Deduplication statistics logging (skipped_count)
7. TTL expiration behavior

Uses fakeredis for isolated, fast testing without external dependencies.
"""

import pytest
import pytest_asyncio
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from fakeredis import FakeAsyncRedis
from app.services.redis_service import RedisService


class TestRedisDeduplication:
    """Test suite for Redis deduplication logic."""

    @pytest_asyncio.fixture
    async def fake_redis_client(self):
        """Fixture providing fake Redis client."""
        client = FakeAsyncRedis(decode_responses=True)
        yield client
        await client.aclose()

    @pytest_asyncio.fixture
    async def redis_service(self, fake_redis_client):
        """Fixture providing RedisService with fake Redis client."""
        service = RedisService()
        # Replace real Redis client with fake one
        service.client = fake_redis_client
        service._available = True
        yield service
        await service.close()

    # =========================================================================
    # Test mark_page_processed() - Key creation with TTL
    # =========================================================================

    @pytest.mark.asyncio
    async def test_mark_page_processed_creates_key(self, redis_service, fake_redis_client):
        """Test that marking a page creates the correct Redis key."""
        crawl_id = "crawl-123"
        source_url = "https://example.com/page1"

        result = await redis_service.mark_page_processed(crawl_id, source_url)

        assert result is True
        # Verify key exists
        key = f"crawl:{crawl_id}:processed"
        exists = await fake_redis_client.exists(key)
        assert exists == 1

    @pytest.mark.asyncio
    async def test_mark_page_processed_sets_ttl(self, redis_service, fake_redis_client):
        """Test that marking a page sets correct TTL (3600 seconds = 1 hour)."""
        crawl_id = "crawl-456"
        source_url = "https://example.com/page2"

        await redis_service.mark_page_processed(crawl_id, source_url)

        key = f"crawl:{crawl_id}:processed"
        ttl = await fake_redis_client.ttl(key)
        # TTL should be 3600 seconds (1 hour)
        assert ttl == 3600

    @pytest.mark.asyncio
    async def test_mark_page_processed_uses_set_data_structure(
        self, redis_service, fake_redis_client
    ):
        """Test that page tracking uses Redis SET for efficient lookups."""
        crawl_id = "crawl-789"
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        key = f"crawl:{crawl_id}:processed"
        # Verify all URLs are in the set
        members = await fake_redis_client.smembers(key)
        assert members == set(urls)

    @pytest.mark.asyncio
    async def test_mark_page_processed_idempotent(self, redis_service, fake_redis_client):
        """Test that marking the same page multiple times is idempotent."""
        crawl_id = "crawl-idempotent"
        source_url = "https://example.com/duplicate"

        # Mark the same page 3 times
        await redis_service.mark_page_processed(crawl_id, source_url)
        await redis_service.mark_page_processed(crawl_id, source_url)
        await redis_service.mark_page_processed(crawl_id, source_url)

        key = f"crawl:{crawl_id}:processed"
        count = await fake_redis_client.scard(key)
        # Should only have 1 entry (set deduplicates)
        assert count == 1

    @pytest.mark.asyncio
    async def test_mark_page_processed_refreshes_ttl(self, redis_service, fake_redis_client):
        """Test that marking an already-processed page refreshes the TTL."""
        crawl_id = "crawl-refresh"
        source_url = "https://example.com/page"

        # Mark page first time
        await redis_service.mark_page_processed(crawl_id, source_url)

        key = f"crawl:{crawl_id}:processed"
        # Manually reduce TTL to simulate time passing
        await fake_redis_client.expire(key, 100)
        ttl_before = await fake_redis_client.ttl(key)
        assert ttl_before == 100

        # Mark again - should refresh TTL back to 3600
        await redis_service.mark_page_processed(crawl_id, source_url)
        ttl_after = await fake_redis_client.ttl(key)
        assert ttl_after == 3600

    @pytest.mark.asyncio
    async def test_mark_page_processed_returns_false_when_redis_unavailable(self):
        """Test graceful handling when Redis is unavailable."""
        service = RedisService()
        service.client = None
        service._available = False

        result = await service.mark_page_processed("crawl-123", "https://example.com")
        assert result is False

    # =========================================================================
    # Test is_page_processed() - Existence checking
    # =========================================================================

    @pytest.mark.asyncio
    async def test_is_page_processed_returns_true_for_marked_page(self, redis_service):
        """Test that is_page_processed returns True for marked pages."""
        crawl_id = "crawl-check-true"
        source_url = "https://example.com/marked"

        await redis_service.mark_page_processed(crawl_id, source_url)
        is_processed = await redis_service.is_page_processed(crawl_id, source_url)

        assert is_processed is True

    @pytest.mark.asyncio
    async def test_is_page_processed_returns_false_for_unmarked_page(self, redis_service):
        """Test that is_page_processed returns False for unmarked pages."""
        crawl_id = "crawl-check-false"
        source_url = "https://example.com/unmarked"

        is_processed = await redis_service.is_page_processed(crawl_id, source_url)

        assert is_processed is False

    @pytest.mark.asyncio
    async def test_is_page_processed_different_crawls_isolated(self, redis_service):
        """Test that different crawl IDs maintain separate tracking."""
        url = "https://example.com/shared"
        crawl_id_1 = "crawl-a"
        crawl_id_2 = "crawl-b"

        # Mark for crawl A only
        await redis_service.mark_page_processed(crawl_id_1, url)

        # Check both crawls
        is_processed_a = await redis_service.is_page_processed(crawl_id_1, url)
        is_processed_b = await redis_service.is_page_processed(crawl_id_2, url)

        assert is_processed_a is True
        assert is_processed_b is False

    @pytest.mark.asyncio
    async def test_is_page_processed_case_sensitive_urls(self, redis_service):
        """Test that URL checking is case-sensitive."""
        crawl_id = "crawl-case"
        url_lower = "https://example.com/page"
        url_upper = "https://example.com/PAGE"

        await redis_service.mark_page_processed(crawl_id, url_lower)

        # Different case should not match
        is_processed_lower = await redis_service.is_page_processed(crawl_id, url_lower)
        is_processed_upper = await redis_service.is_page_processed(crawl_id, url_upper)

        assert is_processed_lower is True
        assert is_processed_upper is False

    @pytest.mark.asyncio
    async def test_is_page_processed_returns_false_when_redis_unavailable(self):
        """Test safe default when Redis is unavailable."""
        service = RedisService()
        service.client = None
        service._available = False

        result = await service.is_page_processed("crawl-123", "https://example.com")
        # Should return False (safe default - process the page)
        assert result is False

    # =========================================================================
    # Test cleanup_crawl_tracking() - Bulk key deletion
    # =========================================================================

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking_deletes_key(
        self, redis_service, fake_redis_client
    ):
        """Test that cleanup removes the tracking key."""
        crawl_id = "crawl-cleanup"
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        # Mark multiple pages
        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        key = f"crawl:{crawl_id}:processed"
        exists_before = await fake_redis_client.exists(key)
        assert exists_before == 1

        # Cleanup
        result = await redis_service.cleanup_crawl_tracking(crawl_id)

        assert result is True
        exists_after = await fake_redis_client.exists(key)
        assert exists_after == 0

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking_removes_all_pages(self, redis_service):
        """Test that cleanup removes all tracked pages."""
        crawl_id = "crawl-cleanup-all"
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        # Mark all pages
        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        # Verify all marked
        for url in urls:
            assert await redis_service.is_page_processed(crawl_id, url) is True

        # Cleanup
        await redis_service.cleanup_crawl_tracking(crawl_id)

        # Verify all removed
        for url in urls:
            assert await redis_service.is_page_processed(crawl_id, url) is False

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking_no_error_for_nonexistent_key(
        self, redis_service
    ):
        """Test that cleanup succeeds even if key doesn't exist."""
        crawl_id = "crawl-never-existed"

        # Cleanup without marking any pages
        result = await redis_service.cleanup_crawl_tracking(crawl_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking_isolates_different_crawls(
        self, redis_service
    ):
        """Test that cleanup only affects the specified crawl."""
        url = "https://example.com/shared"
        crawl_id_1 = "crawl-keep"
        crawl_id_2 = "crawl-remove"

        # Mark pages for both crawls
        await redis_service.mark_page_processed(crawl_id_1, url)
        await redis_service.mark_page_processed(crawl_id_2, url)

        # Cleanup only crawl 2
        await redis_service.cleanup_crawl_tracking(crawl_id_2)

        # Crawl 1 should still have tracking
        assert await redis_service.is_page_processed(crawl_id_1, url) is True
        # Crawl 2 should be cleaned
        assert await redis_service.is_page_processed(crawl_id_2, url) is False

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking_returns_false_when_redis_unavailable(self):
        """Test graceful handling when Redis is unavailable."""
        service = RedisService()
        service.client = None
        service._available = False

        result = await service.cleanup_crawl_tracking("crawl-123")
        assert result is False

    # =========================================================================
    # Test get_processed_count()
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_processed_count_returns_correct_count(self, redis_service):
        """Test that get_processed_count returns accurate count."""
        crawl_id = "crawl-count"
        urls = [f"https://example.com/page{i}" for i in range(10)]

        # Mark 10 pages
        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        count = await redis_service.get_processed_count(crawl_id)
        assert count == 10

    @pytest.mark.asyncio
    async def test_get_processed_count_returns_zero_for_new_crawl(self, redis_service):
        """Test that count is zero for crawl with no pages."""
        crawl_id = "crawl-empty"

        count = await redis_service.get_processed_count(crawl_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_processed_count_handles_duplicates(self, redis_service):
        """Test that count doesn't increase for duplicate pages."""
        crawl_id = "crawl-dup-count"
        url = "https://example.com/page"

        # Mark same page 5 times
        for _ in range(5):
            await redis_service.mark_page_processed(crawl_id, url)

        count = await redis_service.get_processed_count(crawl_id)
        # Should still be 1 (set deduplicates)
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_processed_count_returns_zero_when_redis_unavailable(self):
        """Test safe default when Redis is unavailable."""
        service = RedisService()
        service.client = None
        service._available = False

        count = await service.get_processed_count("crawl-123")
        assert count == 0

    # =========================================================================
    # Test TTL expiration behavior
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ttl_expiration_removes_tracking(self, redis_service, fake_redis_client):
        """Test that expired keys are no longer tracked."""
        crawl_id = "crawl-expire"
        source_url = "https://example.com/expire"

        # Mark page
        await redis_service.mark_page_processed(crawl_id, source_url)

        # Verify marked
        assert await redis_service.is_page_processed(crawl_id, source_url) is True

        # Manually expire the key
        key = f"crawl:{crawl_id}:processed"
        await fake_redis_client.delete(key)

        # Should no longer be tracked
        assert await redis_service.is_page_processed(crawl_id, source_url) is False

    @pytest.mark.asyncio
    async def test_ttl_prevents_indefinite_memory_growth(
        self, redis_service, fake_redis_client
    ):
        """Test that TTL prevents memory leaks from abandoned crawls."""
        crawl_id = "crawl-memory-leak"
        urls = [f"https://example.com/page{i}" for i in range(100)]

        # Mark many pages
        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        key = f"crawl:{crawl_id}:processed"

        # Verify TTL is set
        ttl = await fake_redis_client.ttl(key)
        assert ttl > 0  # TTL is set (3600 seconds)
        assert ttl <= 3600  # Within expected range

        # Simulate expiration
        await fake_redis_client.delete(key)

        # Memory should be freed (key doesn't exist)
        exists = await fake_redis_client.exists(key)
        assert exists == 0

    # =========================================================================
    # Test Redis availability handling
    # =========================================================================

    @pytest.mark.asyncio
    async def test_is_available_returns_true_for_connected_redis(self, redis_service):
        """Test that is_available returns True when Redis is connected."""
        is_available = await redis_service.is_available()
        assert is_available is True

    @pytest.mark.asyncio
    async def test_is_available_returns_false_when_client_none(self):
        """Test that is_available returns False when client is None."""
        service = RedisService()
        service.client = None

        is_available = await service.is_available()
        assert is_available is False

    @pytest.mark.asyncio
    async def test_is_available_returns_false_on_connection_error(self):
        """Test that is_available returns False on ping failure."""
        service = RedisService()
        service.client = MagicMock()
        service.client.ping = AsyncMock(side_effect=Exception("Connection failed"))

        is_available = await service.is_available()
        assert is_available is False

    # =========================================================================
    # Test error handling
    # =========================================================================

    @pytest.mark.asyncio
    async def test_mark_page_processed_handles_redis_error(self, redis_service):
        """Test graceful handling of Redis errors during marking."""
        # Mock sadd to raise exception
        original_client = redis_service.client
        redis_service.client = MagicMock()
        redis_service.client.sadd = AsyncMock(side_effect=Exception("Redis error"))
        redis_service.client.ping = AsyncMock(return_value=True)

        result = await redis_service.mark_page_processed("crawl-123", "https://example.com")

        # Should return False but not crash
        assert result is False

        # Restore original client
        redis_service.client = original_client

    @pytest.mark.asyncio
    async def test_is_page_processed_handles_redis_error(self, redis_service):
        """Test graceful handling of Redis errors during checking."""
        # Mock sismember to raise exception
        original_client = redis_service.client
        redis_service.client = MagicMock()
        redis_service.client.sismember = AsyncMock(side_effect=Exception("Redis error"))
        redis_service.client.ping = AsyncMock(return_value=True)

        result = await redis_service.is_page_processed("crawl-123", "https://example.com")

        # Should return False (safe default)
        assert result is False

        # Restore original client
        redis_service.client = original_client

    @pytest.mark.asyncio
    async def test_cleanup_crawl_tracking_handles_redis_error(self, redis_service):
        """Test graceful handling of Redis errors during cleanup."""
        # Mock delete to raise exception
        original_client = redis_service.client
        redis_service.client = MagicMock()
        redis_service.client.delete = AsyncMock(side_effect=Exception("Redis error"))
        redis_service.client.ping = AsyncMock(return_value=True)

        result = await redis_service.cleanup_crawl_tracking("crawl-123")

        # Should return False but not crash
        assert result is False

        # Restore original client
        redis_service.client = original_client

    # =========================================================================
    # Test concurrent operations (race conditions)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_concurrent_mark_operations_are_safe(self, redis_service):
        """Test that concurrent mark operations don't cause issues."""
        import asyncio

        crawl_id = "crawl-concurrent"
        urls = [f"https://example.com/page{i}" for i in range(50)]

        # Mark all pages concurrently
        await asyncio.gather(
            *[redis_service.mark_page_processed(crawl_id, url) for url in urls]
        )

        # Verify all pages are tracked
        count = await redis_service.get_processed_count(crawl_id)
        assert count == 50

    @pytest.mark.asyncio
    async def test_concurrent_check_operations_are_safe(self, redis_service):
        """Test that concurrent check operations don't cause issues."""
        import asyncio

        crawl_id = "crawl-concurrent-check"
        urls = [f"https://example.com/page{i}" for i in range(50)]

        # Mark all pages
        for url in urls:
            await redis_service.mark_page_processed(crawl_id, url)

        # Check all pages concurrently
        results = await asyncio.gather(
            *[redis_service.is_page_processed(crawl_id, url) for url in urls]
        )

        # All should be True
        assert all(results)

    # =========================================================================
    # Test key format consistency
    # =========================================================================

    @pytest.mark.asyncio
    async def test_key_format_consistency(self, redis_service, fake_redis_client):
        """Test that key format is consistent: crawl:{id}:processed."""
        crawl_id = "test-crawl-123"
        source_url = "https://example.com/page"

        await redis_service.mark_page_processed(crawl_id, source_url)

        # Check that key follows expected format
        expected_key = f"crawl:{crawl_id}:processed"
        exists = await fake_redis_client.exists(expected_key)
        assert exists == 1

    @pytest.mark.asyncio
    async def test_special_characters_in_crawl_id(self, redis_service):
        """Test handling of special characters in crawl ID."""
        crawl_id = "crawl:with:colons-and-dashes_and_underscores"
        source_url = "https://example.com/page"

        # Should handle special characters
        result = await redis_service.mark_page_processed(crawl_id, source_url)
        assert result is True

        is_processed = await redis_service.is_page_processed(crawl_id, source_url)
        assert is_processed is True

    @pytest.mark.asyncio
    async def test_special_characters_in_url(self, redis_service):
        """Test handling of special characters in URL."""
        crawl_id = "crawl-special-url"
        source_url = "https://example.com/page?query=value&foo=bar#section"

        # Should handle URLs with query params and fragments
        result = await redis_service.mark_page_processed(crawl_id, source_url)
        assert result is True

        is_processed = await redis_service.is_page_processed(crawl_id, source_url)
        assert is_processed is True

    @pytest.mark.asyncio
    async def test_unicode_in_url(self, redis_service):
        """Test handling of Unicode characters in URL."""
        crawl_id = "crawl-unicode"
        source_url = "https://example.com/日本語/page"

        # Should handle Unicode URLs
        result = await redis_service.mark_page_processed(crawl_id, source_url)
        assert result is True

        is_processed = await redis_service.is_page_processed(crawl_id, source_url)
        assert is_processed is True


class TestRedisDeduplicationIntegration:
    """Integration tests for deduplication with webhook processing."""

    @pytest_asyncio.fixture
    async def fake_redis_client(self):
        """Fixture providing fake Redis client."""
        client = FakeAsyncRedis(decode_responses=True)
        yield client
        await client.aclose()

    @pytest_asyncio.fixture
    async def mock_redis_service(self, fake_redis_client):
        """Fixture providing mocked RedisService with fake client."""
        service = RedisService()
        service.client = fake_redis_client
        service._available = True
        return service

    # =========================================================================
    # Test streaming mode (crawl.page events)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_streaming_mode_marks_pages_during_crawl_page(
        self, mock_redis_service
    ):
        """Test that streaming mode marks pages as processed during crawl.page."""
        crawl_id = "crawl-streaming"
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        # Simulate streaming mode: mark pages as they arrive
        for url in urls:
            await mock_redis_service.mark_page_processed(crawl_id, url)

        # All pages should be marked
        for url in urls:
            assert await mock_redis_service.is_page_processed(crawl_id, url) is True

        # Count should match
        count = await mock_redis_service.get_processed_count(crawl_id)
        assert count == len(urls)

    # =========================================================================
    # Test batch mode (crawl.completed events)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_batch_mode_skips_already_processed_pages(self, mock_redis_service):
        """Test that batch mode skips pages already processed via streaming."""
        crawl_id = "crawl-batch-dedup"

        # Pages from streaming (already processed)
        streamed_pages = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]

        # New pages in batch
        batch_pages = [
            "https://example.com/page1",  # Duplicate from streaming
            "https://example.com/page2",  # Duplicate from streaming
            "https://example.com/page3",  # New page
        ]

        # Simulate streaming: mark first 2 pages
        for url in streamed_pages:
            await mock_redis_service.mark_page_processed(crawl_id, url)

        # Simulate batch processing: filter out already-processed pages
        new_pages = []
        skipped_count = 0

        for url in batch_pages:
            if await mock_redis_service.is_page_processed(crawl_id, url):
                skipped_count += 1
            else:
                new_pages.append(url)

        # Should skip 2 pages, process 1 new page
        assert skipped_count == 2
        assert len(new_pages) == 1
        assert new_pages[0] == "https://example.com/page3"

    @pytest.mark.asyncio
    async def test_batch_mode_processes_all_when_no_streaming(self, mock_redis_service):
        """Test that batch mode processes all pages when streaming is disabled."""
        crawl_id = "crawl-batch-no-streaming"

        batch_pages = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        # No streaming occurred - all pages should be new
        new_pages = []
        skipped_count = 0

        for url in batch_pages:
            if await mock_redis_service.is_page_processed(crawl_id, url):
                skipped_count += 1
            else:
                new_pages.append(url)

        # Should skip 0, process all 3
        assert skipped_count == 0
        assert len(new_pages) == 3

    # =========================================================================
    # Test deduplication statistics
    # =========================================================================

    @pytest.mark.asyncio
    async def test_deduplication_statistics_logging(self, mock_redis_service, caplog):
        """Test that deduplication statistics are correctly calculated."""
        crawl_id = "crawl-stats"

        # Simulate mixed scenario
        total_pages = 10
        streamed_pages = 6

        # Mark streamed pages
        for i in range(streamed_pages):
            await mock_redis_service.mark_page_processed(
                crawl_id, f"https://example.com/page{i}"
            )

        # Simulate batch processing
        skipped_count = 0
        processed_count = 0

        for i in range(total_pages):
            url = f"https://example.com/page{i}"
            if await mock_redis_service.is_page_processed(crawl_id, url):
                skipped_count += 1
            else:
                processed_count += 1

        # Verify statistics
        assert skipped_count == 6  # Already processed via streaming
        assert processed_count == 4  # New pages in batch
        assert skipped_count + processed_count == total_pages

    @pytest.mark.asyncio
    async def test_all_pages_skipped_scenario(self, mock_redis_service):
        """Test scenario where all pages were already processed via streaming."""
        crawl_id = "crawl-all-skipped"

        urls = [f"https://example.com/page{i}" for i in range(5)]

        # Mark all pages via streaming
        for url in urls:
            await mock_redis_service.mark_page_processed(crawl_id, url)

        # Simulate batch - all should be skipped
        skipped_count = 0
        new_pages = []

        for url in urls:
            if await mock_redis_service.is_page_processed(crawl_id, url):
                skipped_count += 1
            else:
                new_pages.append(url)

        assert skipped_count == 5
        assert len(new_pages) == 0

    @pytest.mark.asyncio
    async def test_cleanup_after_crawl_completion(self, mock_redis_service):
        """Test that cleanup removes all tracking data after crawl completes."""
        crawl_id = "crawl-cleanup-after"

        urls = [f"https://example.com/page{i}" for i in range(5)]

        # Mark pages during crawl
        for url in urls:
            await mock_redis_service.mark_page_processed(crawl_id, url)

        # Verify tracking exists
        count_before = await mock_redis_service.get_processed_count(crawl_id)
        assert count_before == 5

        # Cleanup after completion
        result = await mock_redis_service.cleanup_crawl_tracking(crawl_id)
        assert result is True

        # Verify tracking removed
        count_after = await mock_redis_service.get_processed_count(crawl_id)
        assert count_after == 0

    @pytest.mark.asyncio
    async def test_cleanup_after_crawl_failure(self, mock_redis_service):
        """Test that cleanup removes tracking data even on crawl failure."""
        crawl_id = "crawl-cleanup-failure"

        urls = [f"https://example.com/page{i}" for i in range(3)]

        # Mark some pages before failure
        for url in urls:
            await mock_redis_service.mark_page_processed(crawl_id, url)

        # Verify tracking exists
        count_before = await mock_redis_service.get_processed_count(crawl_id)
        assert count_before == 3

        # Cleanup after failure
        result = await mock_redis_service.cleanup_crawl_tracking(crawl_id)
        assert result is True

        # Verify tracking removed
        count_after = await mock_redis_service.get_processed_count(crawl_id)
        assert count_after == 0

    # =========================================================================
    # Test memory leak prevention
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ttl_prevents_memory_leak_from_abandoned_crawls(
        self, mock_redis_service, fake_redis_client
    ):
        """Test that TTL prevents memory leaks from abandoned crawls."""
        # Simulate multiple abandoned crawls
        abandoned_crawls = [f"crawl-abandoned-{i}" for i in range(10)]

        for crawl_id in abandoned_crawls:
            # Mark pages for abandoned crawl
            for j in range(100):
                await mock_redis_service.mark_page_processed(
                    crawl_id, f"https://example.com/page{j}"
                )

        # Verify all keys have TTL set
        for crawl_id in abandoned_crawls:
            key = f"crawl:{crawl_id}:processed"
            ttl = await fake_redis_client.ttl(key)
            assert ttl > 0  # TTL is set
            assert ttl <= 3600  # Within expected range (1 hour)

        # Simulate expiration (in real scenario, Redis would auto-expire)
        for crawl_id in abandoned_crawls:
            key = f"crawl:{crawl_id}:processed"
            await fake_redis_client.delete(key)

        # Verify memory freed
        for crawl_id in abandoned_crawls:
            count = await mock_redis_service.get_processed_count(crawl_id)
            assert count == 0

    @pytest.mark.asyncio
    async def test_large_crawl_memory_usage(self, mock_redis_service):
        """Test memory usage for large crawls (1000+ pages)."""
        crawl_id = "crawl-large"
        num_pages = 1000

        # Mark 1000 pages
        urls = [f"https://example.com/page{i}" for i in range(num_pages)]
        for url in urls:
            await mock_redis_service.mark_page_processed(crawl_id, url)

        # Verify count
        count = await mock_redis_service.get_processed_count(crawl_id)
        assert count == num_pages

        # Cleanup should handle large sets efficiently
        result = await mock_redis_service.cleanup_crawl_tracking(crawl_id)
        assert result is True

        # Verify cleanup
        count_after = await mock_redis_service.get_processed_count(crawl_id)
        assert count_after == 0

    # =========================================================================
    # Test Redis unavailable scenarios
    # =========================================================================

    @pytest.mark.asyncio
    async def test_deduplication_disabled_when_redis_unavailable(self):
        """Test that deduplication is gracefully disabled when Redis is unavailable."""
        service = RedisService()
        service.client = None
        service._available = False

        crawl_id = "crawl-no-redis"
        urls = ["https://example.com/page1", "https://example.com/page2"]

        # All operations should return safe defaults
        for url in urls:
            result = await service.mark_page_processed(crawl_id, url)
            assert result is False  # Failed to mark

        # Checking should always return False (not processed)
        for url in urls:
            is_processed = await service.is_page_processed(crawl_id, url)
            assert is_processed is False  # Safe default: process the page

        # This means when Redis is down, all pages will be processed
        # (no deduplication, but no data loss)
