"""
Cache management endpoints for query result caching.
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel
from typing import Dict, Any
from app.services.query_cache import QueryCache
from app.dependencies import get_query_cache

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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset cache stats: {str(e)}"
        )
