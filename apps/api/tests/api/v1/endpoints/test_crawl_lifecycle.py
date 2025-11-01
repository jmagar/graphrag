"""
Tests for crawl endpoint lifecycle and dependency injection.

Tests that endpoints properly use the singleton FirecrawlService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.dependencies import set_firecrawl_service, clear_firecrawl_service


class TestCrawlEndpointLifecycle:
    """Test suite for crawl endpoint lifecycle management."""

    @pytest.mark.anyio
    async def test_crawl_endpoint_uses_singleton_service(self, test_client):
        """
        Test that multiple requests use the same FirecrawlService instance via dependency injection.
        """
        # Create a mock service
        mock_service = MagicMock()
        mock_service.start_crawl = AsyncMock(return_value={
            "id": "test-crawl-123",
            "success": True,
            "url": "https://example.com"
        })
        
        # Set the mock service as the singleton
        set_firecrawl_service(mock_service)
        
        try:
            # Make first request
            response1 = await test_client.post(
                "/api/v1/crawl/",
                json={
                    "url": "https://example.com",
                    "limit": 10
                }
            )
            
            # Make second request
            response2 = await test_client.post(
                "/api/v1/crawl/",
                json={
                    "url": "https://example.org",
                    "limit": 10
                }
            )
            
            # Both should succeed
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Service method should be called twice (same instance)
            assert mock_service.start_crawl.call_count == 2
        finally:
            # Clean up
            clear_firecrawl_service()
