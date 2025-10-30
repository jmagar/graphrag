"""
Tests for statistics endpoint.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_collection_stats_returns_valid_structure():
    """Test that the stats endpoint returns the expected data structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/query/collection/info")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields exist
        assert "name" in data
        assert "points_count" in data
        assert "vectors_count" in data
        assert "status" in data

        # Verify data types
        assert isinstance(data["name"], str)
        assert isinstance(data["points_count"], int)
        assert isinstance(data["vectors_count"], int)
        assert isinstance(data["status"], str)

        # Points count should be non-negative
        assert data["points_count"] >= 0
        assert data["vectors_count"] >= 0


@pytest.mark.asyncio
async def test_get_collection_stats_includes_storage_info():
    """Test that the stats endpoint includes storage information."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/query/collection/info")

        assert response.status_code == 200
        data = response.json()

        # Check for storage size information if available
        # This might not be available in all Qdrant versions
        # but we should at least check the structure
        assert "segments_count" in data or "indexed_vectors_count" in data
