"""Tests for QueryCache service."""

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
import time

from app.services.query_cache import QueryCache


@pytest.mark.asyncio
class TestQueryCacheBasics:
    """Test basic query cache functionality."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def query_cache(self, fake_redis):
        """Create QueryCache with fake Redis."""
        cache = QueryCache(redis_client=fake_redis, default_ttl=60)
        yield cache

    async def test_cache_initialization(self, fake_redis):
        """Test QueryCache can be initialized."""
        cache = QueryCache(redis_client=fake_redis, default_ttl=300)
        assert cache is not None
        assert cache.default_ttl == 300
        assert cache.enabled is True

    async def test_cache_miss_returns_none(self, query_cache):
        """Test cache miss returns None."""
        collection = "test_collection"
        query = "nonexistent query"

        result = await query_cache.get(collection, query)
        assert result is None

    async def test_cache_hit_returns_cached_data(self, query_cache):
        """Test cache hit returns previously cached data."""
        collection = "test_collection"
        query = "test query"
        results = {"data": [{"id": 1, "content": "test"}]}

        # Store in cache
        await query_cache.set(collection, query, results, query_time_ms=50.0)

        # Retrieve from cache
        cached = await query_cache.get(collection, query)

        assert cached is not None
        assert cached == results

    async def test_cache_set_and_get_with_different_queries(self, query_cache):
        """Test cache correctly stores different queries independently."""
        collection = "test_collection"

        # Store multiple queries
        await query_cache.set(collection, "query1", [1], query_time_ms=10.0)
        await query_cache.set(collection, "query2", [2], query_time_ms=10.0)
        await query_cache.set(collection, "query3", [3], query_time_ms=10.0)

        # Retrieve each
        result1 = await query_cache.get(collection, "query1")
        result2 = await query_cache.get(collection, "query2")
        result3 = await query_cache.get(collection, "query3")

        assert result1 == [1]
        assert result2 == [2]
        assert result3 == [3]

    async def test_cache_different_collections_independent(self, query_cache):
        """Test cache maintains independence between collections."""
        query = "same query"

        # Store same query in different collections
        await query_cache.set("collection1", query, {"data": "collection1"}, query_time_ms=10.0)
        await query_cache.set("collection2", query, {"data": "collection2"}, query_time_ms=10.0)

        # Retrieve from each collection
        result1 = await query_cache.get("collection1", query)
        result2 = await query_cache.get("collection2", query)

        assert result1["data"] == "collection1"
        assert result2["data"] == "collection2"

    async def test_cache_overwrites_existing_entry(self, query_cache):
        """Test setting same key overwrites previous value."""
        collection = "test_collection"
        query = "test query"

        # Store initial value
        await query_cache.set(collection, query, {"version": 1}, query_time_ms=10.0)

        # Overwrite with new value
        await query_cache.set(collection, query, {"version": 2}, query_time_ms=10.0)

        # Retrieve - should get new value
        cached = await query_cache.get(collection, query)
        assert cached["version"] == 2


@pytest.mark.asyncio
class TestCacheStatistics:
    """Test cache statistics tracking."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def query_cache(self, fake_redis):
        """Create QueryCache with fake Redis."""
        return QueryCache(redis_client=fake_redis)

    async def test_initial_statistics_are_zero(self, query_cache):
        """Test cache statistics start at zero."""
        stats = query_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_requests"] == 0

    async def test_cache_miss_increments_miss_count(self, query_cache):
        """Test cache miss increments miss counter."""
        await query_cache.get("collection", "query")

        stats = query_cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    async def test_cache_hit_increments_hit_count(self, query_cache):
        """Test cache hit increments hit counter."""
        # Store data
        await query_cache.set("collection", "query", {"data": "test"}, query_time_ms=10.0)

        # First get is a hit
        await query_cache.get("collection", "query")

        stats = query_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    async def test_hit_rate_calculation(self, query_cache):
        """Test hit rate is calculated correctly."""
        # 1 hit, 1 miss
        await query_cache.set("collection", "query", {"data": 1}, query_time_ms=10.0)
        await query_cache.get("collection", "query")  # hit
        await query_cache.get("collection", "nonexistent")  # miss

        stats = query_cache.get_stats()
        assert stats["hit_rate"] == 50.0

    async def test_reset_statistics(self, query_cache):
        """Test resetting cache statistics."""
        await query_cache.set("collection", "query", {"data": "test"}, query_time_ms=10.0)
        await query_cache.get("collection", "query")
        await query_cache.get("collection", "miss")

        # Reset
        query_cache.reset_stats()

        stats = query_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Test cache invalidation functionality."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def query_cache(self, fake_redis):
        """Create QueryCache with fake Redis."""
        return QueryCache(redis_client=fake_redis)

    async def test_invalidate_entire_collection(self, query_cache):
        """Test invalidating all queries for a collection."""
        collection = "test"

        # Cache multiple queries for the collection
        await query_cache.set(collection, "query1", {"data": 1}, query_time_ms=10.0)
        await query_cache.set(collection, "query2", {"data": 2}, query_time_ms=10.0)
        await query_cache.set(collection, "query3", {"data": 3}, query_time_ms=10.0)

        # Cache query for different collection
        await query_cache.set("other_collection", "query4", {"data": 4}, query_time_ms=10.0)

        # Invalidate test collection
        deleted = await query_cache.invalidate_collection(collection)
        assert deleted == 3

        # Queries from invalidated collection should return None
        assert await query_cache.get(collection, "query1") is None
        assert await query_cache.get(collection, "query2") is None
        assert await query_cache.get(collection, "query3") is None

        # Other collection should still have cached data
        assert await query_cache.get("other_collection", "query4") == {"data": 4}

    async def test_invalidate_all_caches(self, query_cache):
        """Test invalidating all cached queries across all collections."""
        # Cache queries across multiple collections
        await query_cache.set("collection1", "query1", {"data": 1}, query_time_ms=10.0)
        await query_cache.set("collection2", "query2", {"data": 2}, query_time_ms=10.0)
        await query_cache.set("collection3", "query3", {"data": 3}, query_time_ms=10.0)

        # Invalidate all
        deleted = await query_cache.invalidate_all()
        assert deleted == 3

        # All queries should return None
        assert await query_cache.get("collection1", "query1") is None
        assert await query_cache.get("collection2", "query2") is None
        assert await query_cache.get("collection3", "query3") is None


@pytest.mark.asyncio
class TestCacheWithQueryParameters:
    """Test cache handles query parameters correctly."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def query_cache(self, fake_redis):
        """Create QueryCache with fake Redis."""
        return QueryCache(redis_client=fake_redis)

    async def test_cache_respects_limit_parameter(self, query_cache):
        """Test cache keys differ based on limit parameter."""
        collection = "test"
        query = "test query"

        # Cache with limit=3
        await query_cache.set(collection, query, [1, 2, 3], query_time_ms=10.0, limit=3)
        # Cache with limit=5
        await query_cache.set(collection, query, [1, 2, 3, 4, 5], query_time_ms=10.0, limit=5)

        # Should retrieve correct results based on limit
        result_3 = await query_cache.get(collection, query, limit=3)
        result_5 = await query_cache.get(collection, query, limit=5)

        assert result_3 == [1, 2, 3]
        assert result_5 == [1, 2, 3, 4, 5]

    async def test_cache_respects_score_threshold(self, query_cache):
        """Test cache keys differ based on score_threshold parameter."""
        collection = "test"
        query = "test"

        await query_cache.set(
            collection, query, [{"score": 0.9}], query_time_ms=10.0, score_threshold=0.8
        )
        await query_cache.set(
            collection, query, [{"score": 0.95}], query_time_ms=10.0, score_threshold=0.9
        )

        result_08 = await query_cache.get(collection, query, score_threshold=0.8)
        result_09 = await query_cache.get(collection, query, score_threshold=0.9)

        assert result_08[0]["score"] == 0.9
        assert result_09[0]["score"] == 0.95

    async def test_cache_with_filters(self, query_cache):
        """Test cache handles filter parameters correctly."""
        collection = "test"
        query = "test"

        await query_cache.set(
            collection,
            query,
            [{"type": "doc"}],
            query_time_ms=10.0,
            filters={"type": "doc"},
        )
        await query_cache.set(
            collection,
            query,
            [{"type": "image"}],
            query_time_ms=10.0,
            filters={"type": "image"},
        )

        doc_results = await query_cache.get(collection, query, filters={"type": "doc"})
        img_results = await query_cache.get(collection, query, filters={"type": "image"})

        assert doc_results[0]["type"] == "doc"
        assert img_results[0]["type"] == "image"


@pytest.mark.asyncio
class TestCacheDisabled:
    """Test cache behavior when disabled."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    async def test_cache_disabled_returns_none(self, fake_redis):
        """Test disabled cache always returns None."""
        cache = QueryCache(redis_client=fake_redis, enabled=False)

        # Try to cache data
        await cache.set("collection", "query", {"data": "test"}, query_time_ms=10.0)

        # Should return None since cache is disabled
        result = await cache.get("collection", "query")
        assert result is None

    async def test_cache_disabled_stats_show_disabled(self, fake_redis):
        """Test stats show cache is disabled."""
        cache = QueryCache(redis_client=fake_redis, enabled=False)

        stats = cache.get_stats()
        assert stats["enabled"] is False


@pytest.mark.asyncio
class TestCachePerformance:
    """Test cache performance characteristics."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def query_cache(self, fake_redis):
        """Create QueryCache with fake Redis."""
        return QueryCache(redis_client=fake_redis)

    async def test_cache_reduces_query_time(self, query_cache):
        """Test cached queries are faster than initial queries."""
        collection = "test"
        query = "expensive query"
        expensive_results = {"data": [{"id": i} for i in range(1000)]}

        # Cache the expensive results
        await query_cache.set(collection, query, expensive_results, query_time_ms=500.0)

        # Measure cached retrieval time
        start = time.time()
        cached_results = await query_cache.get(collection, query)
        cached_time = (time.time() - start) * 1000  # Convert to ms

        assert cached_results == expensive_results
        # Cached retrieval should be very fast with fakeredis (< 50ms)
        assert cached_time < 50

    async def test_bulk_cache_operations(self, query_cache):
        """Test performance with many cache operations."""
        collection = "test"

        # Cache 100 different queries
        start = time.time()
        for i in range(100):
            await query_cache.set(collection, f"query_{i}", [i], query_time_ms=10.0)
        set_time = time.time() - start

        # Retrieve all
        start = time.time()
        for i in range(100):
            result = await query_cache.get(collection, f"query_{i}")
            assert result == [i]
        get_time = time.time() - start

        # With fakeredis, both should complete quickly
        assert set_time < 1.0  # 1 second
        assert get_time < 1.0  # 1 second


@pytest.mark.asyncio
class TestCacheIntegrationScenarios:
    """Test realistic cache usage scenarios."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def query_cache(self, fake_redis):
        """Create QueryCache with fake Redis."""
        return QueryCache(redis_client=fake_redis)

    async def test_typical_query_workflow(self, query_cache):
        """Test typical RAG query workflow with caching."""
        collection = "graphrag"
        query = "What is GraphRAG?"
        query_results = {
            "results": [
                {"id": "doc1", "content": "GraphRAG explanation", "score": 0.95}
            ]
        }

        # First query - cache miss
        cached = await query_cache.get(collection, query)
        assert cached is None

        # Cache the results
        await query_cache.set(collection, query, query_results, query_time_ms=150.0)

        # Second query - cache hit
        cached = await query_cache.get(collection, query)
        assert cached == query_results

        stats = query_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    async def test_cache_invalidation_after_collection_update(self, query_cache):
        """Test cache invalidation after document updates."""
        collection = "graphrag"

        # Cache some queries
        await query_cache.set(collection, "query1", [1], query_time_ms=10.0)
        await query_cache.set(collection, "query2", [2], query_time_ms=10.0)

        # Document added to collection - invalidate cache
        await query_cache.invalidate_collection(collection)

        # Queries should return None after invalidation
        assert await query_cache.get(collection, "query1") is None
        assert await query_cache.get(collection, "query2") is None

    async def test_concurrent_cache_access(self, query_cache):
        """Test concurrent cache access works correctly."""
        import asyncio

        collection = "test"

        # Cache initial data
        await query_cache.set(collection, "shared_query", {"data": "initial"}, query_time_ms=10.0)

        # Concurrent reads
        async def read_cache(query_id):
            return await query_cache.get(collection, "shared_query")

        results = await asyncio.gather(
            read_cache(1), read_cache(2), read_cache(3), read_cache(4), read_cache(5)
        )

        # All should return the same cached data
        for result in results:
            assert result == {"data": "initial"}

        stats = query_cache.get_stats()
        assert stats["hits"] == 5
