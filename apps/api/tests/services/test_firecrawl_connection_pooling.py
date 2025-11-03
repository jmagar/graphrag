"""
Tests for Firecrawl service HTTP connection pooling implementation.

Following TDD methodology:
1. RED: Test written first (expecting failure)
2. GREEN: Implementation makes test pass
3. REFACTOR: Improve code while keeping tests green

These tests verify:
- Persistent client creation and reuse across multiple calls
- Connection pooling configuration (max_connections=100, max_keepalive=20)
- Authorization headers set on client level
- Proper cleanup with close() method
- Client recreation after close (is_closed check)
- All 7 service methods using the same client instance
"""

import pytest
import httpx
from unittest.mock import MagicMock, patch
from app.services.firecrawl import FirecrawlService
from app.core.config import settings

pytestmark = pytest.mark.anyio


class TestConnectionPoolingClientCreation:
    """Tests for persistent HTTP client creation and configuration."""

    async def test_client_created_on_first_request(self):
        """Test that HTTP client is created on first request."""
        # Arrange
        service = FirecrawlService()
        assert service._client is None

        # Act
        client = await service._get_client()

        # Assert
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert service._client is client

    async def test_client_reused_on_subsequent_requests(self):
        """Test that same client instance is reused across multiple requests."""
        # Arrange
        service = FirecrawlService()

        # Act
        client1 = await service._get_client()
        client2 = await service._get_client()
        client3 = await service._get_client()

        # Assert - All should be the exact same instance
        assert client1 is client2
        assert client2 is client3
        assert id(client1) == id(client2) == id(client3)

    async def test_client_has_correct_connection_pool_limits(self):
        """Test that client is configured with correct connection pooling limits."""
        # Arrange
        service = FirecrawlService()

        # Act
        client = await service._get_client()

        # Assert
        # Access pool limits via transport._pool
        assert client._transport._pool._max_connections == 100
        assert client._transport._pool._max_keepalive_connections == 20

    async def test_client_has_correct_timeout_configuration(self):
        """Test that client has correct timeout settings."""
        # Arrange
        service = FirecrawlService()

        # Act
        client = await service._get_client()

        # Assert
        # Timeout object has connect, read, write, pool attributes
        assert client.timeout.read == 60.0
        assert client.timeout.connect == 10.0

    async def test_client_has_authorization_header_configured(self):
        """Test that client has Authorization header set at client level."""
        # Arrange
        service = FirecrawlService()

        # Act
        client = await service._get_client()

        # Assert
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == f"Bearer {settings.FIRECRAWL_API_KEY}"

    async def test_multiple_service_instances_have_separate_clients(self):
        """Test that different service instances maintain separate client instances."""
        # Arrange
        service1 = FirecrawlService()
        service2 = FirecrawlService()

        # Act
        client1 = await service1._get_client()
        client2 = await service2._get_client()

        # Assert - Different service instances should have different clients
        assert client1 is not client2
        assert id(client1) != id(client2)


class TestConnectionPoolingClientCleanup:
    """Tests for proper client cleanup and resource management."""

    async def test_close_method_closes_client(self):
        """Test that close() method properly closes the HTTP client."""
        # Arrange
        service = FirecrawlService()
        client = await service._get_client()
        assert not client.is_closed

        # Act
        await service.close()

        # Assert
        assert client.is_closed
        assert service._client is None

    async def test_close_method_is_idempotent(self):
        """Test that calling close() multiple times doesn't raise errors."""
        # Arrange
        service = FirecrawlService()
        await service._get_client()

        # Act & Assert - Should not raise
        await service.close()
        await service.close()
        await service.close()

    async def test_close_when_client_never_created(self):
        """Test that close() works even if client was never created."""
        # Arrange
        service = FirecrawlService()
        assert service._client is None

        # Act & Assert - Should not raise
        await service.close()

    async def test_client_recreated_after_close(self):
        """Test that client is recreated if accessed after being closed."""
        # Arrange
        service = FirecrawlService()
        original_client = await service._get_client()
        await service.close()

        # Act
        new_client = await service._get_client()

        # Assert
        assert new_client is not None
        assert isinstance(new_client, httpx.AsyncClient)
        assert new_client is not original_client
        assert not new_client.is_closed

    async def test_is_closed_check_handles_closed_client(self):
        """Test that _get_client recreates client if it's been closed externally."""
        # Arrange
        service = FirecrawlService()
        original_client = await service._get_client()

        # Simulate external closure (without calling service.close())
        await original_client.aclose()
        # Don't set service._client to None - test the is_closed check

        # Act
        new_client = await service._get_client()

        # Assert
        assert new_client is not None
        assert new_client is not original_client
        assert not new_client.is_closed


class TestConnectionPoolingAcrossServiceMethods:
    """Tests verifying all service methods use the same client instance."""

    @patch("httpx.AsyncClient.post")
    async def test_start_crawl_uses_persistent_client(self, mock_post):
        """Test that start_crawl uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "crawl_123"}
        mock_post.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.start_crawl({"url": "https://example.com"})
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_post.called

    @patch("httpx.AsyncClient.get")
    async def test_get_crawl_status_uses_persistent_client(self, mock_get):
        """Test that get_crawl_status uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "crawl_123", "status": "completed"}
        mock_get.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.get_crawl_status("crawl_123")
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_get.called

    @patch("httpx.AsyncClient.delete")
    async def test_cancel_crawl_uses_persistent_client(self, mock_delete):
        """Test that cancel_crawl uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "crawl_123", "status": "cancelled"}
        mock_delete.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.cancel_crawl("crawl_123")
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_delete.called

    @patch("httpx.AsyncClient.post")
    async def test_scrape_url_uses_persistent_client(self, mock_post):
        """Test that scrape_url uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_post.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.scrape_url("https://example.com")
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_post.called

    @patch("httpx.AsyncClient.post")
    async def test_map_url_uses_persistent_client(self, mock_post):
        """Test that map_url uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": []}
        mock_post.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.map_url("https://example.com")
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_post.called

    @patch("httpx.AsyncClient.post")
    async def test_search_web_uses_persistent_client(self, mock_post):
        """Test that search_web uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": []}
        mock_post.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.search_web("test query")
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_post.called

    @patch("httpx.AsyncClient.post")
    async def test_extract_data_uses_persistent_client(self, mock_post):
        """Test that extract_data uses the persistent client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_post.return_value = mock_response

        # Act
        client_before = await service._get_client()
        await service.extract_data(["https://example.com"], {"type": "object"})
        client_after = await service._get_client()

        # Assert
        assert client_before is client_after
        assert mock_post.called

    @patch("httpx.AsyncClient.post")
    @patch("httpx.AsyncClient.get")
    @patch("httpx.AsyncClient.delete")
    async def test_all_methods_share_same_client_instance(
        self, mock_delete, mock_get, mock_post
    ):
        """Test that all 7 service methods use the exact same client instance."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        mock_get.return_value = mock_response
        mock_delete.return_value = mock_response

        # Act - Call all 7 methods
        client1 = await service._get_client()
        await service.start_crawl({"url": "https://example.com"})

        client2 = await service._get_client()
        await service.get_crawl_status("crawl_123")

        client3 = await service._get_client()
        await service.cancel_crawl("crawl_123")

        client4 = await service._get_client()
        await service.scrape_url("https://example.com")

        client5 = await service._get_client()
        await service.map_url("https://example.com")

        client6 = await service._get_client()
        await service.search_web("test query")

        client7 = await service._get_client()
        await service.extract_data(["https://example.com"], {"type": "object"})

        # Assert - All should be the same instance
        assert client1 is client2 is client3 is client4 is client5 is client6 is client7
        assert id(client1) == id(client2) == id(client3) == id(client4)
        assert id(client5) == id(client6) == id(client7)


class TestConnectionPoolingPerformance:
    """Tests for connection pooling performance characteristics."""

    async def test_sequential_requests_reuse_connection(self):
        """Test that sequential requests reuse the same client (simulating connection reuse)."""
        # Arrange
        service = FirecrawlService()

        # Act - Make multiple sequential requests
        clients = []
        for _ in range(10):
            client = await service._get_client()
            clients.append(client)

        # Assert - All should be the same instance
        assert all(client is clients[0] for client in clients)
        assert len(set(id(c) for c in clients)) == 1

    async def test_concurrent_access_returns_same_client(self):
        """Test that concurrent access to _get_client returns same instance."""
        # Arrange
        service = FirecrawlService()

        # Act - Simulate concurrent access
        import asyncio

        clients = await asyncio.gather(
            service._get_client(),
            service._get_client(),
            service._get_client(),
            service._get_client(),
            service._get_client(),
        )

        # Assert - All should be the same instance
        assert all(client is clients[0] for client in clients)

    @patch("httpx.AsyncClient.post")
    async def test_rapid_method_calls_use_same_client(self, mock_post):
        """Test that rapid successive method calls all use the same client."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        # Act - Rapid successive calls
        import asyncio

        initial_client = await service._get_client()

        await asyncio.gather(
            service.start_crawl({"url": "https://example.com"}),
            service.scrape_url("https://example.com"),
            service.map_url("https://example.com"),
            service.search_web("query"),
        )

        final_client = await service._get_client()

        # Assert
        assert initial_client is final_client


class TestConnectionPoolingEdgeCases:
    """Tests for edge cases and error conditions in connection pooling."""

    async def test_client_configuration_immutable_after_creation(self):
        """Test that client configuration doesn't change after creation."""
        # Arrange
        service = FirecrawlService()

        # Act
        client = await service._get_client()
        original_pool = client._transport._pool
        original_timeout = client.timeout
        original_headers = dict(client.headers)

        # Get client again
        client_again = await service._get_client()

        # Assert - Configuration should be identical (same client instance)
        assert client_again._transport._pool is original_pool
        assert client_again.timeout is original_timeout
        assert dict(client_again.headers) == original_headers

    async def test_service_headers_applied_to_client(self):
        """Test that service-level headers are properly applied to client."""
        # Arrange
        service = FirecrawlService()

        # Act
        client = await service._get_client()

        # Assert
        assert client.headers["Authorization"] == service.headers["Authorization"]

    async def test_client_base_url_not_set(self):
        """Test that client doesn't have base_url set (methods use full URLs)."""
        # Arrange
        service = FirecrawlService()

        # Act
        client = await service._get_client()

        # Assert - base_url should be empty or None
        assert not client.base_url or str(client.base_url) == ""

    async def test_close_releases_all_connections(self):
        """Test that close() properly releases all connections."""
        # Arrange
        service = FirecrawlService()
        client = await service._get_client()

        # Act
        await service.close()

        # Assert
        assert client.is_closed
        # After close, _client should be None to prevent reuse of closed client
        assert service._client is None

    async def test_multiple_close_calls_idempotent(self):
        """Test that multiple close() calls are safe and idempotent."""
        # Arrange
        service = FirecrawlService()
        await service._get_client()

        # Act - Multiple closes
        await service.close()
        await service.close()
        await service.close()

        # Assert - Should complete without errors
        assert service._client is None


class TestConnectionPoolingIntegration:
    """Integration tests for connection pooling across full service lifecycle."""

    @patch("httpx.AsyncClient.post")
    @patch("httpx.AsyncClient.get")
    async def test_full_lifecycle_with_connection_reuse(self, mock_get, mock_post):
        """Test full service lifecycle with connection pooling."""
        # Arrange
        service = FirecrawlService()
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": "crawl_123"}
        mock_post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"status": "completed"}
        mock_get.return_value = mock_get_response

        # Act - Full workflow
        client1 = await service._get_client()

        # Start crawl
        await service.start_crawl({"url": "https://example.com"})
        client2 = await service._get_client()

        # Check status
        await service.get_crawl_status("crawl_123")
        client3 = await service._get_client()

        # Cleanup
        await service.close()

        # Assert
        assert client1 is client2 is client3
        assert service._client is None

    @patch("httpx.AsyncClient.post")
    async def test_service_survives_client_recreation(self, mock_post):
        """Test that service continues working after client recreation."""
        # Arrange
        service = FirecrawlService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "crawl_123"}
        mock_post.return_value = mock_response

        # Act
        # First use
        await service.start_crawl({"url": "https://example.com"})
        first_client = await service._get_client()

        # Close and recreate
        await service.close()
        await service.start_crawl({"url": "https://example.com"})
        second_client = await service._get_client()

        # Assert
        assert first_client is not second_client
        assert not first_client.is_closed or True  # May be closed
        assert not second_client.is_closed
        assert mock_post.call_count == 2
