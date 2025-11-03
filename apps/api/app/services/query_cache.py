"""
Redis-backed query result cache for improving RAG query performance.

Provides:
- Query result caching with configurable TTL
- Cache key generation from query + parameters
- Cache invalidation by pattern
- Cache statistics (hit/miss ratio)
"""

import hashlib
import json
import logging
import time
from typing import Any, Optional, Dict, List
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class QueryCache:
    """Redis-backed query result cache."""

    def __init__(
        self,
        redis_client: Redis,
        default_ttl: int = 300,  # 5 minutes
        enabled: bool = True,
    ):
        """
        Initialize query cache.

        Args:
            redis_client: Async Redis client instance
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            enabled: Whether caching is enabled (default: True)
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.enabled = enabled
        self._stats = {"hits": 0, "misses": 0}

    def _generate_cache_key(
        self, collection: str, query_text: str, **params: Any
    ) -> str:
        """
        Generate deterministic cache key from query parameters.

        Args:
            collection: Collection name (e.g., "graphrag")
            query_text: Query text
            **params: Additional query parameters (limit, filters, etc.)

        Returns:
            Cache key in format: query_cache:v1:{collection}:{query_hash}
        """
        # Create deterministic string from query + params
        cache_input = f"{collection}:{query_text}:{json.dumps(params, sort_keys=True)}"
        query_hash = hashlib.md5(cache_input.encode()).hexdigest()
        return f"query_cache:v1:{collection}:{query_hash}"

    async def get(
        self, collection: str, query_text: str, **params: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached query result.

        Args:
            collection: Collection name
            query_text: Query text
            **params: Query parameters

        Returns:
            Cached results dict, or None if not found or cache disabled
        """
        if not self.enabled:
            return None

        try:
            key = self._generate_cache_key(collection, query_text, **params)
            data = await self.redis.get(key)

            if data:
                self._stats["hits"] += 1
                cached: Dict[str, Any] = json.loads(data)
                logger.debug(f"Cache HIT for {collection}: {query_text[:50]}...")

                # Update hit count
                cached["metadata"]["hit_count"] = (
                    cached["metadata"].get("hit_count", 0) + 1
                )
                await self.redis.set(key, json.dumps(cached), ex=self.default_ttl)

                results: Dict[str, Any] = cached["results"]
                return results

            self._stats["misses"] += 1
            logger.debug(f"Cache MISS for {collection}: {query_text[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self._stats["misses"] += 1
            return None

    async def set(
        self,
        collection: str,
        query_text: str,
        results: Any,
        query_time_ms: float,
        ttl: Optional[int] = None,
        **params: Any,
    ) -> None:
        """
        Cache query result.

        Args:
            collection: Collection name
            query_text: Query text
            results: Query results to cache
            query_time_ms: Query execution time in milliseconds
            ttl: Optional TTL override (defaults to default_ttl)
            **params: Query parameters
        """
        if not self.enabled:
            return

        try:
            key = self._generate_cache_key(collection, query_text, **params)
            cached_data = {
                "results": results,
                "metadata": {
                    "timestamp": time.time(),
                    "query_time_ms": query_time_ms,
                    "hit_count": 0,
                    "collection": collection,
                },
            }

            ttl = ttl or self.default_ttl
            await self.redis.set(key, json.dumps(cached_data), ex=ttl)
            logger.debug(f"Cached query for {collection} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    async def invalidate_collection(self, collection: str) -> int:
        """
        Invalidate all cached queries for a collection.

        Args:
            collection: Collection name

        Returns:
            Number of cache entries deleted
        """
        try:
            pattern = f"query_cache:v1:{collection}:*"
            keys: List[str] = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted: int = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for {collection}")
                return deleted
            return 0

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0

    async def invalidate_all(self) -> int:
        """
        Invalidate all cached queries.

        Returns:
            Number of cache entries deleted
        """
        try:
            pattern = "query_cache:v1:*"
            keys: List[str] = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted: int = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} total cache entries")
                return deleted
            return 0

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit_rate, and total_requests
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate * 100, 2),
            "total_requests": total,
            "enabled": self.enabled,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0}
        logger.info("Cache statistics reset")
