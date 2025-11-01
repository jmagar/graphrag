"""
Integration tests for webhook deduplication.

Tests verify that pages processed during crawl.page events
are skipped in crawl.completed events to avoid duplicate processing.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


class TestWebhookDeduplication:
    """Test suite for webhook deduplication logic."""

    @pytest.fixture
    def client(self):
        """Fixture providing test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_page_data(self):
        """Fixture providing sample page data."""
        return {
            "markdown": "# Test Page\n\nThis is test content.",
            "metadata": {
                "sourceURL": "https://example.com/page1",
                "title": "Test Page",
            },
        }

    @pytest.mark.asyncio
    async def test_crawl_page_marks_page_as_processed(
        self, client, sample_page_data
    ):
        """Test that crawl.page events mark pages as processed."""
        with patch("app.api.v1.endpoints.webhooks.process_crawled_page") as mock_process:
            with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
                mock_redis.mark_page_processed = AsyncMock(return_value=True)
                
                payload = {
                    "type": "crawl.page",
                    "id": "test-crawl-123",
                    "data": sample_page_data,
                }

                response = client.post("/api/v1/webhooks/firecrawl", json=payload)

                assert response.status_code == 200
                assert response.json()["status"] == "processing"
                
                # Verify page was marked as processed
                mock_redis.mark_page_processed.assert_called_once_with(
                    "test-crawl-123",
                    "https://example.com/page1"
                )

    @pytest.mark.asyncio
    async def test_crawl_completed_skips_processed_pages(self, client, sample_page_data):
        """Test that crawl.completed skips pages already processed via streaming."""
        with patch(
            "app.api.v1.endpoints.webhooks.process_and_store_documents_batch"
        ) as mock_batch:
            with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
                # Mock that page was already processed
                mock_redis.is_page_processed = AsyncMock(return_value=True)
                mock_redis.cleanup_crawl_tracking = AsyncMock(return_value=True)
                
                payload = {
                    "type": "crawl.completed",
                    "id": "test-crawl-123",
                    "data": [sample_page_data],  # Same page
                }

                response = client.post("/api/v1/webhooks/firecrawl", json=payload)

                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "completed"
                assert result["pages_processed"] == 1
                assert result["pages_skipped"] == 1

                # Verify batch processing was NOT called (all pages skipped)
                mock_batch.assert_not_called()
                
                # Verify cleanup was called
                mock_redis.cleanup_crawl_tracking.assert_called_once_with(
                    "test-crawl-123"
                )

    @pytest.mark.asyncio
    async def test_crawl_completed_processes_new_pages(self, client):
        """Test that crawl.completed processes pages not seen during streaming."""
        new_page = {
            "markdown": "# New Page\n\nNew content.",
            "metadata": {
                "sourceURL": "https://example.com/new-page",
                "title": "New Page",
            },
        }

        with patch(
            "app.api.v1.endpoints.webhooks.process_and_store_documents_batch"
        ) as mock_batch:
            with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
                # Mock that page was NOT processed
                mock_redis.is_page_processed = AsyncMock(return_value=False)
                mock_redis.cleanup_crawl_tracking = AsyncMock(return_value=True)
                
                payload = {
                    "type": "crawl.completed",
                    "id": "test-crawl-456",
                    "data": [new_page],
                }

                response = client.post("/api/v1/webhooks/firecrawl", json=payload)

                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "completed"
                assert result["pages_processed"] == 1
                assert result["pages_skipped"] == 0

                # Verify batch processing WAS called with new page
                mock_batch.assert_called_once()
                
                # Get the documents passed to batch processor
                call_args = mock_batch.call_args[0][0]
                assert len(call_args) == 1
                assert call_args[0]["source_url"] == "https://example.com/new-page"

    @pytest.mark.asyncio
    async def test_mixed_processed_and_new_pages(self, client, sample_page_data):
        """Test handling mix of already-processed and new pages."""
        new_page = {
            "markdown": "# Another Page",
            "metadata": {
                "sourceURL": "https://example.com/page2",
                "title": "Another Page",
            },
        }

        with patch(
            "app.api.v1.endpoints.webhooks.process_and_store_documents_batch"
        ) as mock_batch:
            with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
                # First page processed, second page new
                async def is_processed_side_effect(crawl_id, url):
                    return url == "https://example.com/page1"
                
                mock_redis.is_page_processed = AsyncMock(side_effect=is_processed_side_effect)
                mock_redis.cleanup_crawl_tracking = AsyncMock(return_value=True)
                
                payload = {
                    "type": "crawl.completed",
                    "id": "test-crawl-789",
                    "data": [sample_page_data, new_page],
                }

                response = client.post("/api/v1/webhooks/firecrawl", json=payload)

                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "completed"
                assert result["pages_processed"] == 2
                assert result["pages_skipped"] == 1

                # Verify only new page was batched
                mock_batch.assert_called_once()
                call_args = mock_batch.call_args[0][0]
                assert len(call_args) == 1
                assert call_args[0]["source_url"] == "https://example.com/page2"

    @pytest.mark.asyncio
    async def test_streaming_disabled_skips_page_processing(
        self, client, sample_page_data
    ):
        """Test that streaming can be disabled via config flag."""
        with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
            with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
                mock_settings.ENABLE_STREAMING_PROCESSING = False
                mock_redis.mark_page_processed = AsyncMock(return_value=True)
                
                payload = {
                    "type": "crawl.page",
                    "id": "test-crawl-disabled",
                    "data": sample_page_data,
                }

                response = client.post("/api/v1/webhooks/firecrawl", json=payload)

                assert response.status_code == 200
                assert response.json()["status"] == "acknowledged"
                
                # Page still tracked for deduplication
                mock_redis.mark_page_processed.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_failed_cleans_up_tracking(self, client):
        """Test that failed crawls clean up tracking data."""
        with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
            mock_redis.cleanup_crawl_tracking = AsyncMock(return_value=True)
            
            payload = {
                "type": "crawl.failed",
                "id": "test-crawl-failed",
                "error": "Test error message",
            }

            response = client.post("/api/v1/webhooks/firecrawl", json=payload)

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "error"
            assert result["error"] == "Test error message"
            
            # Verify cleanup was called
            mock_redis.cleanup_crawl_tracking.assert_called_once_with(
                "test-crawl-failed"
            )

    @pytest.mark.asyncio
    async def test_handles_redis_unavailable_gracefully(
        self, client, sample_page_data
    ):
        """Test graceful handling when Redis is unavailable."""
        with patch(
            "app.api.v1.endpoints.webhooks.process_and_store_documents_batch"
        ) as mock_batch:
            with patch("app.api.v1.endpoints.webhooks.redis_service") as mock_redis:
                # Simulate Redis unavailable
                mock_redis.is_page_processed = AsyncMock(return_value=False)
                mock_redis.mark_page_processed = AsyncMock(return_value=False)
                
                payload = {
                    "type": "crawl.completed",
                    "id": "test-crawl-redis-down",
                    "data": [sample_page_data],
                }

                response = client.post("/api/v1/webhooks/firecrawl", json=payload)

                # Should still process successfully (falls back to processing all)
                assert response.status_code == 200
                assert response.json()["status"] == "completed"
                
                # All pages processed (no deduplication when Redis down)
                mock_batch.assert_called_once()
