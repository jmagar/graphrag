"""
Redis service for caching and tracking crawl operations.

Provides methods for:
- Tracking processed pages during crawl operations
- Query embedding caching
- Deduplication of webhook events
"""

import logging
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Service for Redis operations."""

    def __init__(self):
        """Initialize Redis client with connection pooling."""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self._available = True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without Redis.")
            self.client = None
            self._available = False

    async def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    async def mark_page_processed(self, crawl_id: str, source_url: str) -> bool:
        """
        Mark a page as processed for a crawl.

        Args:
            crawl_id: Unique identifier for the crawl job
            source_url: Source URL of the processed page

        Returns:
            True if marked successfully, False if Redis unavailable
        """
        if not await self.is_available():
            logger.debug("Redis unavailable, skipping page tracking")
            return False

        try:
            key = f"crawl:{crawl_id}:processed"
            await self.client.sadd(key, source_url)
            await self.client.expire(key, 3600)  # 1 hour TTL
            logger.debug(f"Marked page as processed: {source_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark page as processed: {e}")
            return False

    async def is_page_processed(self, crawl_id: str, source_url: str) -> bool:
        """
        Check if a page was already processed for a crawl.

        Args:
            crawl_id: Unique identifier for the crawl job
            source_url: Source URL to check

        Returns:
            True if page was already processed, False otherwise
        """
        if not await self.is_available():
            logger.debug("Redis unavailable, assuming page not processed")
            return False

        try:
            key = f"crawl:{crawl_id}:processed"
            result = await self.client.sismember(key, source_url)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check if page processed: {e}")
            return False

    async def get_processed_count(self, crawl_id: str) -> int:
        """
        Get count of processed pages for a crawl.

        Args:
            crawl_id: Unique identifier for the crawl job

        Returns:
            Number of processed pages, or 0 if Redis unavailable
        """
        if not await self.is_available():
            return 0

        try:
            key = f"crawl:{crawl_id}:processed"
            count = await self.client.scard(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get processed count: {e}")
            return 0

    async def cleanup_crawl_tracking(self, crawl_id: str) -> bool:
        """
        Clean up tracking data for a completed crawl.

        Args:
            crawl_id: Unique identifier for the crawl job

        Returns:
            True if cleanup successful, False otherwise
        """
        if not await self.is_available():
            return False

        try:
            key = f"crawl:{crawl_id}:processed"
            await self.client.delete(key)
            logger.info(f"Cleaned up tracking data for crawl: {crawl_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup crawl tracking: {e}")
            return False

    async def cache_query_embedding(
        self, query: str, embedding: list[float], ttl: int = 3600
    ) -> bool:
        """
        Cache a query embedding for faster subsequent searches.

        Args:
            query: The search query text
            embedding: The embedding vector
            ttl: Time-to-live in seconds (default: 1 hour)

        Returns:
            True if cached successfully, False otherwise
        """
        if not await self.is_available():
            return False

        try:
            import json
            import hashlib

            # Use hash of query as key
            query_hash = hashlib.md5(query.encode()).hexdigest()
            key = f"embed:query:{query_hash}"

            # Store as JSON
            value = json.dumps({"query": query, "embedding": embedding})
            await self.client.set(key, value, ex=ttl)
            logger.debug(f"Cached embedding for query: {query[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to cache query embedding: {e}")
            return False

    async def get_cached_embedding(self, query: str) -> Optional[list[float]]:
        """
        Retrieve cached embedding for a query.

        Args:
            query: The search query text

        Returns:
            Cached embedding vector, or None if not found or Redis unavailable
        """
        if not await self.is_available():
            return None

        try:
            import json
            import hashlib

            query_hash = hashlib.md5(query.encode()).hexdigest()
            key = f"embed:query:{query_hash}"

            value = await self.client.get(key)
            if value:
                data = json.loads(value)
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return data.get("embedding")

            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Failed to get cached embedding: {e}")
            return None

    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
