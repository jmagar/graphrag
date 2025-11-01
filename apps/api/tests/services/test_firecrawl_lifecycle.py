"""
Tests for FirecrawlService lifecycle and resource management.

Tests that HTTP connections are properly managed and cleaned up.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.firecrawl import FirecrawlService


class TestFirecrawlServiceLifecycle:
    """Test suite for FirecrawlService resource lifecycle."""

    @pytest.mark.anyio
    async def test_firecrawl_service_creates_client_on_first_use(self):
        """
        Test that client is None before first API call and created lazily.
        
        RED: This test should PASS initially (behavior already works).
        """
        service = FirecrawlService()
        
        # Client should be None initially
        assert service._client is None
        
        # After first API call, client should be created
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = {"id": "test-123", "success": True, "url": "https://example.com"}
            
            await service.start_crawl({"url": "https://example.com"})
            
            # Client should now exist
            assert service._client is not None

    @pytest.mark.anyio
    async def test_firecrawl_service_reuses_client(self):
        """
        Test that multiple API calls use the same client instance.
        
        RED: This test should PASS initially (behavior already works).
        """
        service = FirecrawlService()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = {"id": "test-123", "success": True, "url": "https://example.com"}
            
            # Make first call
            await service.start_crawl({"url": "https://example.com"})
            first_client = service._client
            
            # Make second call
            await service.start_crawl({"url": "https://example.com"})
            second_client = service._client
            
            # Should be the same instance
            assert first_client is second_client

    @pytest.mark.anyio
    async def test_firecrawl_service_close_releases_connections(self):
        """
        Test that close() properly releases connections and sets client to None.
        
        RED: This test will FAIL initially (close() doesn't handle errors).
        """
        service = FirecrawlService()
        
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        service._client = mock_client
        
        # Close the service
        await service.close()
        
        # Client should be closed
        mock_client.aclose.assert_called_once()
        
        # Client should be set to None
        assert service._client is None

    @pytest.mark.anyio
    async def test_firecrawl_service_close_handles_errors(self):
        """
        Test that close() doesn't raise exceptions if client already closed.
        
        RED: This test will FAIL initially (no error handling).
        """
        service = FirecrawlService()
        
        # Create a mock client that raises an error on close
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock(side_effect=RuntimeError("Connection already closed"))
        service._client = mock_client
        
        # close() should not raise an exception
        await service.close()
        
        # Client should still be set to None
        assert service._client is None
        
        # Calling close again should be safe
        await service.close()  # Should not raise

    @pytest.mark.anyio
    async def test_firecrawl_service_context_manager(self):
        """
        Test that context manager automatically closes client on exit.
        
        RED: This test will FAIL initially (context manager not implemented).
        """
        service = FirecrawlService()
        
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        
        async with service:
            service._client = mock_client
            assert service._client is not None
        
        # After exiting context, client should be closed
        mock_client.aclose.assert_called_once()
        assert service._client is None

    @pytest.mark.anyio
    async def test_firecrawl_service_is_closed_property(self):
        """
        Test the is_closed property for health checks.
        
        RED: This test will FAIL initially (property not implemented).
        """
        service = FirecrawlService()
        
        # Initially no client, so should be considered "closed"
        assert service.is_closed is True
        
        # Create a mock client
        mock_client = MagicMock()
        mock_client.is_closed = False
        service._client = mock_client
        
        # Now should not be closed
        assert service.is_closed is False
        
        # Mark client as closed
        mock_client.is_closed = True
        assert service.is_closed is True
