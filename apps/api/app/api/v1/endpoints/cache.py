"""
Cache management endpoints for query result caching.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, ValidationError
from typing import Dict, Any
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from app.services.query_cache import QueryCache
from app.dependencies import get_query_cache

logger = logging.getLogger(__name__)
router = APIRouter()


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    hits: int
    misses: int
    hit_rate: float
    total_requests: int
    enabled: bool


class CacheInvalidateResponse(BaseModel):
    """Response model for cache invalidation."""

    deleted_count: int
    message: str


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(query_cache: QueryCache = Depends(get_query_cache)):
    """
    Get query cache statistics including hit/miss ratio.

    Returns cache performance metrics:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - hit_rate: Cache hit rate as percentage
    - total_requests: Total number of cache requests
    - enabled: Whether caching is enabled
    """
    try:
        stats = query_cache.get_stats()
        return CacheStatsResponse(**stats)

    except ValidationError as e:
        logger.exception("Validation error getting cache stats")
        raise HTTPException(status_code=422, detail=f"Invalid stats response: {str(e)}")

    except RedisConnectionError:
        logger.exception("Redis connection error getting cache stats")
        raise HTTPException(status_code=503, detail="Cache service unavailable")

    except RedisError as e:
        logger.exception("Redis error getting cache stats")
        raise HTTPException(status_code=500, detail=f"Cache error: {str(e)}")

    except Exception as e:
        logger.exception("Unexpected error getting cache stats")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.delete("/invalidate/all", response_model=CacheInvalidateResponse)
async def invalidate_all_cache(query_cache: QueryCache = Depends(get_query_cache)):
    """
    Invalidate all cached query results.

    This clears the entire query cache across all collections.
    Use with caution as this will force all queries to be re-executed.
    """
    # TODO: Add authentication/authorization before production deployment
    # These endpoints should be:
    # 1. Behind admin-only authentication, OR
    # 2. Protected by API key, OR
    # 3. Rate-limited and firewall-protected
    # Current implementation is NOT production-safe without additional security
    try:
        deleted_count = await query_cache.invalidate_all()
        return CacheInvalidateResponse(
            deleted_count=deleted_count,
            message=f"Invalidated {deleted_count} cache entries",
        )

    except asyncio.TimeoutError:
        logger.exception("Timeout error invalidating all cache")
        raise HTTPException(status_code=504, detail="Cache invalidation timed out. Please try again.")

    except RedisConnectionError:
        logger.exception("Redis connection error invalidating all cache")
        raise HTTPException(status_code=503, detail="Cache service unavailable")

    except RedisError as e:
        logger.exception("Redis error invalidating all cache")
        raise HTTPException(status_code=500, detail=f"Cache error: {str(e)}")

    except Exception as e:
        logger.exception("Unexpected error invalidating all cache")
        raise HTTPException(
            status_code=500, detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.delete("/invalidate/collection/{collection}", response_model=CacheInvalidateResponse)
async def invalidate_collection_cache(
    collection: str = Path(..., regex="^[a-zA-Z0-9_-]+$", max_length=100),
    query_cache: QueryCache = Depends(get_query_cache)
):
    """
    Invalidate all cached query results for a specific collection.

    Args:
        collection: Collection name (e.g., "graphrag", "hybrid")

    This clears cached queries for a specific collection.
    Useful when documents are updated in that collection.
    """
    # TODO: Add authentication/authorization before production deployment
    # These endpoints should be:
    # 1. Behind admin-only authentication, OR
    # 2. Protected by API key, OR
    # 3. Rate-limited and firewall-protected
    # Current implementation is NOT production-safe without additional security
    try:
        deleted_count = await query_cache.invalidate_collection(collection)
        return CacheInvalidateResponse(
            deleted_count=deleted_count,
            message=f"Invalidated {deleted_count} cache entries for collection '{collection}'",
        )

    except asyncio.TimeoutError:
        logger.exception(f"Timeout error invalidating cache for collection '{collection}'")
        raise HTTPException(status_code=504, detail="Cache invalidation timed out. Please try again.")

    except RedisConnectionError:
        logger.exception(f"Redis connection error invalidating cache for collection '{collection}'")
        raise HTTPException(status_code=503, detail="Cache service unavailable")

    except RedisError as e:
        logger.exception(f"Redis error invalidating cache for collection '{collection}'")
        raise HTTPException(status_code=500, detail=f"Cache error: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error invalidating cache for collection '{collection}'")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache for collection '{collection}': {str(e)}",
        )


@router.post("/stats/reset")
async def reset_cache_stats(query_cache: QueryCache = Depends(get_query_cache)) -> Dict[str, Any]:
    """
    Reset cache statistics counters.

    This resets hit/miss counters to zero without clearing the actual cache.
    Useful for benchmarking or testing cache performance.
    """
    try:
        query_cache.reset_stats()
        return {"message": "Cache statistics reset successfully"}

    except RedisConnectionError:
        logger.exception("Redis connection error resetting cache stats")
        raise HTTPException(status_code=503, detail="Cache service unavailable")

    except RedisError as e:
        logger.exception("Redis error resetting cache stats")
        raise HTTPException(status_code=500, detail=f"Cache error: {str(e)}")

    except Exception as e:
        logger.exception("Unexpected error resetting cache stats")
        raise HTTPException(
            status_code=500, detail=f"Failed to reset cache stats: {str(e)}"
        )
