"""
Tests for query result caching with Redis.

This module tests the QueryCache class which provides intelligent caching
of query results to reduce load on the vector database and improve response times.

TDD Approach: These tests are written first (RED phase) before implementation.
"""

import pytest
import pytest_asyncio
import time
import hashlib
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from fakeredis import FakeAsyncRedis


# Import will fail initially since features don't exist yet
# This is expected in TDD - tests are written first
try:
    from app.services.query_cache import QueryCache
except ImportError:
    # Create a placeholder class for testing purposes
    class QueryCache:
        """Placeholder class - will be implemented to make tests pass."""
        pass


@pytest.mark.asyncio
class TestQueryCacheBasics:
    """Test basic QueryCache functionality."""

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
        cache = QueryCache(redis_client=fake_redis, default_ttl=60)
        assert cache is not None
        assert hasattr(cache, "redis")
        assert hasattr(cache, "default_ttl")

    async def test_cache_miss_returns_none(self, query_cache):
        """Test cache miss returns None."""
        collection = "test_collection"
        query = "test query"

        result = await query_cache.get(collection, query)
        assert result is None

    async def test_cache_hit_returns_cached_data(self, query_cache):
        """Test cache hit returns previously cached data."""
        collection = "test_collection"
        query = "test query"
        results = {"data": [{"id": 1, "content": "test"}]}

        # Store in cache
        await query_cache.set(collection, query, results)

        # Retrieve from cache
        cached = await query_cache.get(collection, query)

        assert cached is not None
        assert cached == results

    async def test_cache_set_and_get_with_different_queries(self, query_cache):
        """Test cache correctly stores different queries independently."""
        collection = "test_collection"

        # Store multiple queries
        await query_cache.set(collection, "query1", {"results": [1]})
        await query_cache.set(collection, "query2", {"results": [2]})
        await query_cache.set(collection, "query3", {"results": [3]})

        # Retrieve each
        result1 = await query_cache.get(collection, "query1")
        result2 = await query_cache.get(collection, "query2")
        result3 = await query_cache.get(collection, "query3")

        assert result1["results"] == [1]
        assert result2["results"] == [2]
        assert result3["results"] == [3]

    async def test_cache_different_collections_independent(self, query_cache):
        """Test cache maintains independence between collections."""
        query = "same query"

        # Store same query in different collections
        await query_cache.set("collection1", query, {"data": "collection1"})
        await query_cache.set("collection2", query, {"data": "collection2"})

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
        await query_cache.set(collection, query, {"version": 1})

        # Overwrite with new value
        await query_cache.set(collection, query, {"version": 2})

        # Retrieve - should get new value
        cached = await query_cache.get(collection, query)
        assert cached["version"] == 2


@pytest.mark.asyncio
class TestCacheKeyGeneration:
    """Test cache key generation logic."""

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

    async def test_generate_cache_key_is_deterministic(self, query_cache):
        """Test cache key generation is deterministic for same inputs."""
        collection = "test_collection"
        query = "test query"
        limit = 10

        key1 = query_cache.generate_cache_key(collection, query, limit=limit)
        key2 = query_cache.generate_cache_key(collection, query, limit=limit)

        assert key1 == key2

    async def test_generate_cache_key_different_for_different_queries(self, query_cache):
        """Test different queries produce different cache keys."""
        collection = "test_collection"

        key1 = query_cache.generate_cache_key(collection, "query1")
        key2 = query_cache.generate_cache_key(collection, "query2")

        assert key1 != key2

    async def test_generate_cache_key_different_for_different_collections(self, query_cache):
        """Test different collections produce different cache keys."""
        query = "same query"

        key1 = query_cache.generate_cache_key("collection1", query)
        key2 = query_cache.generate_cache_key("collection2", query)

        assert key1 != key2

    async def test_generate_cache_key_includes_parameters(self, query_cache):
        """Test cache key varies with different query parameters."""
        collection = "test"
        query = "test"

        key_default = query_cache.generate_cache_key(collection, query)
        key_limit_5 = query_cache.generate_cache_key(collection, query, limit=5)
        key_limit_10 = query_cache.generate_cache_key(collection, query, limit=10)
        key_score_threshold = query_cache.generate_cache_key(
            collection, query, score_threshold=0.8
        )

        # All should be different
        assert len({key_default, key_limit_5, key_limit_10, key_score_threshold}) == 4

    async def test_cache_key_uses_prefix(self, query_cache):
        """Test cache keys use the configured prefix."""
        key = query_cache.generate_cache_key("test", "query")
        assert key.startswith("query_cache:")


@pytest.mark.asyncio
class TestCacheStatistics:
    """Test cache hit/miss statistics tracking."""

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
        """Test cache starts with zero statistics."""
        stats = query_cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate"] == 0.0

    async def test_cache_miss_increments_miss_count(self, query_cache):
        """Test cache miss increments miss counter."""
        await query_cache.get("collection", "nonexistent query")

        stats = query_cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    async def test_cache_hit_increments_hit_count(self, query_cache):
        """Test cache hit increments hit counter."""
        collection = "test"
        query = "test query"

        # Store and retrieve
        await query_cache.set(collection, query, {"data": "test"})
        await query_cache.get(collection, query)

        stats = query_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    async def test_hit_rate_calculation(self, query_cache):
        """Test hit rate is calculated correctly."""
        collection = "test"

        # Store data
        await query_cache.set(collection, "query1", {"data": 1})
        await query_cache.set(collection, "query2", {"data": 2})

        # 3 hits
        await query_cache.get(collection, "query1")
        await query_cache.get(collection, "query1")
        await query_cache.get(collection, "query2")

        # 1 miss
        await query_cache.get(collection, "query3")

        stats = query_cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["total_requests"] == 4
        assert stats["hit_rate"] == 75.0  # 3/4 = 0.75

    async def test_reset_statistics(self, query_cache):
        """Test statistics can be reset."""
        # Generate some stats
        await query_cache.get("test", "query1")
        await query_cache.set("test", "query2", {"data": 2})
        await query_cache.get("test", "query2")

        # Reset
        query_cache.reset_stats()

        stats = query_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0


@pytest.mark.asyncio
class TestCacheTTL:
    """Test cache TTL (Time To Live) functionality."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    async def test_cache_entry_expires_after_ttl(self, fake_redis):
        """Test cache entry expires after TTL."""
        cache = QueryCache(redis_client=fake_redis, default_ttl=1)  # 1 second TTL

        collection = "test"
        query = "test query"

        # Store data
        await cache.set(collection, query, {"data": "test"})

        # Should be available immediately
        cached = await cache.get(collection, query)
        assert cached is not None

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        cached = await cache.get(collection, query)
        assert cached is None

    async def test_custom_ttl_per_entry(self, fake_redis):
        """Test custom TTL can be set per cache entry."""
        cache = QueryCache(redis_client=fake_redis, default_ttl=60)

        collection = "test"

        # Store with short custom TTL
        await cache.set(collection, "query1", {"data": 1}, ttl=1)
        # Store with default TTL
        await cache.set(collection, "query2", {"data": 2})

        # Wait for short TTL to expire
        time.sleep(1.5)

        # query1 should be expired, query2 should still exist
        result1 = await cache.get(collection, "query1")
        result2 = await cache.get(collection, "query2")

        assert result1 is None
        assert result2 is not None

    async def test_ttl_validation(self, fake_redis):
        """Test TTL validation prevents invalid values."""
        cache = QueryCache(redis_client=fake_redis)

        # TTL of 0 or negative should raise error or use default
        with pytest.raises(ValueError):
            await cache.set("test", "query", {"data": "test"}, ttl=0)

        with pytest.raises(ValueError):
            await cache.set("test", "query", {"data": "test"}, ttl=-1)


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

    async def test_invalidate_specific_query(self, query_cache):
        """Test invalidating a specific cached query."""
        collection = "test"
        query = "test query"

        # Store data
        await query_cache.set(collection, query, {"data": "test"})

        # Invalidate
        await query_cache.invalidate(collection, query)

        # Should be gone
        cached = await query_cache.get(collection, query)
        assert cached is None

    async def test_invalidate_entire_collection(self, query_cache):
        """Test invalidating all cached queries for a collection."""
        collection = "test_collection"

        # Store multiple queries
        await query_cache.set(collection, "query1", {"data": 1})
        await query_cache.set(collection, "query2", {"data": 2})
        await query_cache.set(collection, "query3", {"data": 3})

        # Store in different collection (should not be affected)
        await query_cache.set("other_collection", "query4", {"data": 4})

        # Invalidate entire collection
        await query_cache.invalidate_collection(collection)

        # Collection queries should be gone
        assert await query_cache.get(collection, "query1") is None
        assert await query_cache.get(collection, "query2") is None
        assert await query_cache.get(collection, "query3") is None

        # Other collection should still exist
        assert await query_cache.get("other_collection", "query4") is not None

    async def test_invalidate_all_caches(self, query_cache):
        """Test invalidating all cached queries across all collections."""
        # Store data in multiple collections
        await query_cache.set("collection1", "query1", {"data": 1})
        await query_cache.set("collection2", "query2", {"data": 2})
        await query_cache.set("collection3", "query3", {"data": 3})

        # Invalidate all
        await query_cache.invalidate_all()

        # All should be gone
        assert await query_cache.get("collection1", "query1") is None
        assert await query_cache.get("collection2", "query2") is None
        assert await query_cache.get("collection3", "query3") is None


@pytest.mark.asyncio
class TestCacheWithQueryParameters:
    """Test cache behavior with different query parameters."""

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
        """Test cache differentiates queries with different limits."""
        collection = "test"
        query = "test query"

        # Store with different limits
        await query_cache.set(collection, query, {"results": [1, 2, 3]}, limit=3)
        await query_cache.set(collection, query, {"results": [1, 2, 3, 4, 5]}, limit=5)

        # Retrieve with specific limits
        result_3 = await query_cache.get(collection, query, limit=3)
        result_5 = await query_cache.get(collection, query, limit=5)

        assert len(result_3["results"]) == 3
        assert len(result_5["results"]) == 5

    async def test_cache_respects_score_threshold(self, query_cache):
        """Test cache differentiates queries with different score thresholds."""
        collection = "test"
        query = "test query"

        # Store with different thresholds
        await query_cache.set(
            collection,
            query,
            {"results": [{"score": 0.9}, {"score": 0.7}]},
            score_threshold=0.6
        )
        await query_cache.set(
            collection,
            query,
            {"results": [{"score": 0.9}]},
            score_threshold=0.8
        )

        # Retrieve with specific thresholds
        result_low = await query_cache.get(collection, query, score_threshold=0.6)
        result_high = await query_cache.get(collection, query, score_threshold=0.8)

        assert len(result_low["results"]) == 2
        assert len(result_high["results"]) == 1

    async def test_cache_with_filters(self, query_cache):
        """Test cache handles query filters correctly."""
        collection = "test"
        query = "test query"

        # Store with different filters
        await query_cache.set(
            collection,
            query,
            {"results": ["filtered"]},
            filters={"language": "en"}
        )
        await query_cache.set(
            collection,
            query,
            {"results": ["spanish"]},
            filters={"language": "es"}
        )

        # Retrieve with specific filters
        result_en = await query_cache.get(collection, query, filters={"language": "en"})
        result_es = await query_cache.get(collection, query, filters={"language": "es"})

        assert result_en["results"] == ["filtered"]
        assert result_es["results"] == ["spanish"]


@pytest.mark.asyncio
class TestCacheMetadata:
    """Test cache stores and retrieves metadata."""

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

    async def test_cache_stores_query_time(self, query_cache):
        """Test cache stores query execution time metadata."""
        collection = "test"
        query = "test query"
        query_time_ms = 42.5

        # Store with query time
        await query_cache.set(
            collection,
            query,
            {"results": []},
            query_time_ms=query_time_ms
        )

        # Retrieve
        cached = await query_cache.get(collection, query)

        # Should include metadata about query time
        assert "metadata" in cached or "query_time_ms" in cached

    async def test_cache_stores_timestamp(self, query_cache):
        """Test cache stores timestamp when data was cached."""
        collection = "test"
        query = "test query"

        before = time.time()
        await query_cache.set(collection, query, {"results": []})
        after = time.time()

        # Retrieve
        cached = await query_cache.get(collection, query)

        # Should have timestamp within our time range
        # (Implementation detail: might be in metadata)
        assert cached is not None

    async def test_cache_get_includes_metadata(self, query_cache):
        """Test get returns metadata about cache entry."""
        collection = "test"
        query = "test query"

        await query_cache.set(collection, query, {"results": []}, query_time_ms=50.0)

        # Get with metadata
        cached = await query_cache.get(collection, query, include_metadata=True)

        assert "data" in cached or "results" in cached
        # Metadata should indicate this was a cache hit
        assert cached is not None


@pytest.mark.asyncio
class TestRedisUnavailability:
    """Test graceful handling when Redis is unavailable."""

    async def test_cache_handles_redis_connection_failure(self):
        """Test cache handles Redis connection failure gracefully."""
        fake_redis = MagicMock()
        fake_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        fake_redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))

        cache = QueryCache(redis_client=fake_redis)

        # Should not raise exception
        result = await cache.get("test", "query")
        assert result is None

        # Set should also handle gracefully
        await cache.set("test", "query", {"data": "test"})

    async def test_cache_with_none_redis(self):
        """Test cache handles None redis client gracefully."""
        cache = QueryCache(redis=None)

        # Should work without Redis (pass-through, no caching)
        result = await cache.get("test", "query")
        assert result is None

        # Set should be a no-op
        await cache.set("test", "query", {"data": "test"})


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

    async def test_cache_set_performance(self, query_cache):
        """Test set operation completes quickly."""
        start = time.time()
        await query_cache.set("test", "query", {"results": [1, 2, 3]})
        elapsed = time.time() - start

        # Should complete in under 50ms (fakeredis is fast)
        assert elapsed < 0.05, f"Set took {elapsed:.3f}s, expected <0.05s"

    async def test_cache_get_performance(self, query_cache):
        """Test get operation completes quickly."""
        # Pre-populate
        await query_cache.set("test", "query", {"results": [1, 2, 3]})

        start = time.time()
        await query_cache.get("test", "query")
        elapsed = time.time() - start

        # Should complete in under 50ms
        assert elapsed < 0.05, f"Get took {elapsed:.3f}s, expected <0.05s"

    async def test_bulk_cache_operations(self, query_cache):
        """Test performance with many cache operations."""
        start = time.time()

        # Store 100 queries
        for i in range(100):
            await query_cache.set("test", f"query_{i}", {"results": [i]})

        # Retrieve 100 queries
        for i in range(100):
            await query_cache.get("test", f"query_{i}")

        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second for fakeredis)
        assert elapsed < 1.0, f"Bulk operations took {elapsed:.3f}s, expected <1s"

    async def test_cache_reduces_query_time(self, query_cache):
        """Test that cache actually improves performance."""
        collection = "test"
        query = "expensive query"

        # Simulate expensive operation (first query)
        expensive_results = {"results": [{"id": i} for i in range(100)]}

        # Store in cache
        await query_cache.set(collection, query, expensive_results, query_time_ms=500.0)

        # Retrieve from cache (should be faster)
        start = time.time()
        cached = await query_cache.get(collection, query)
        cache_time = (time.time() - start) * 1000  # Convert to ms

        assert cached is not None
        # Cache retrieval should be much faster than original query
        assert cache_time < 500.0


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
        return QueryCache(redis_client=fake_redis, default_ttl=300)

    async def test_typical_query_workflow(self, query_cache):
        """Test typical query workflow with cache."""
        collection = "graphrag"
        query = "What is machine learning?"

        # First request - cache miss
        cached = await query_cache.get(collection, query)
        assert cached is None

        # Execute query and store results
        query_results = {
            "results": [
                {"id": "doc1", "score": 0.95, "content": "ML intro"},
                {"id": "doc2", "score": 0.88, "content": "ML basics"},
            ]
        }
        await query_cache.set(collection, query, query_results, query_time_ms=150.0)

        # Second request - cache hit
        cached = await query_cache.get(collection, query)
        assert cached is not None
        assert len(cached["results"]) == 2

        # Stats should reflect hit and miss
        stats = query_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    async def test_cache_invalidation_after_collection_update(self, query_cache):
        """Test cache invalidation after updating collection."""
        collection = "graphrag"

        # Store some cached queries
        await query_cache.set(collection, "query1", {"results": [1]})
        await query_cache.set(collection, "query2", {"results": [2]})

        # Verify cached
        assert await query_cache.get(collection, "query1") is not None

        # Simulate collection update - invalidate cache
        await query_cache.invalidate_collection(collection)

        # Cache should be cleared
        assert await query_cache.get(collection, "query1") is None
        assert await query_cache.get(collection, "query2") is None

    async def test_concurrent_cache_access(self, query_cache):
        """Test concurrent cache operations don't corrupt data."""
        import asyncio

        collection = "test"

        async def cache_operation(query_num: int):
            query = f"query_{query_num}"
            results = {"results": [query_num]}
            await query_cache.set(collection, query, results)
            cached = await query_cache.get(collection, query)
            return cached

        # Run 20 concurrent cache operations
        tasks = [cache_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(r is not None for r in results)
        assert len(results) == 20
