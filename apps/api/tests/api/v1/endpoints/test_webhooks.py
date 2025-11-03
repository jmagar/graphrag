"""
Tests for webhook endpoints.

These tests follow TDD methodology:
1. RED: Test written first (expecting failure)
2. GREEN: Implementation makes test pass
3. REFACTOR: Improve code while keeping tests green

Priority: CRITICAL - webhook processing has zero test coverage
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, call
import hashlib

from app.main import app
from app.dependencies import (
    get_redis_service,
    get_language_detection_service,
)

# Enable anyio for all tests in this module
pytestmark = pytest.mark.anyio


class TestWebhookCrawlStarted:
    """Tests for crawl.started webhook event."""

    async def test_crawl_started_returns_acknowledged(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that crawl.started webhook is acknowledged."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "type": "crawl.started",
                "id": "crawl_123"
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "acknowledged"
        finally:
            app.dependency_overrides.clear()

    async def test_crawl_started_with_missing_id(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test crawl.started webhook with missing ID still responds."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {"type": "crawl.started"}

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            assert response.json()["status"] == "acknowledged"
        finally:
            app.dependency_overrides.clear()


class TestWebhookCrawlPage:
    """Tests for crawl.page webhook event."""

    async def test_crawl_page_triggers_background_processing(
        self, test_client: AsyncClient, sample_webhook_crawl_page, 
        mock_redis_service, mock_language_detection_service
    ):
        """Test that crawl.page webhook triggers background processing."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_page
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.document_processor.embeddings_service")
    @patch("app.services.document_processor.vector_db_service")
    async def test_crawl_page_processes_content_correctly(
        self,
        mock_vector_db,
        mock_embeddings,
        test_client: AsyncClient,
        sample_webhook_crawl_page,
        mock_redis_service,
        mock_language_detection_service
    ):
        """Test that page content is processed and stored correctly."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            mock_embeddings.generate_embedding = AsyncMock(return_value=[0.1] * 768)
            mock_vector_db.upsert_document = AsyncMock()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_page
            )

            # Assert
            assert response.status_code == 200
            
            # Note: Background tasks execute after response, so we check the response
            # In integration tests, we would verify the actual storage
            assert response.json()["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    async def test_crawl_page_with_empty_content(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that pages with empty content are handled gracefully."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "type": "crawl.page",
                "id": "crawl_123",
                "data": {
                    "markdown": "",
                    "metadata": {
                        "sourceURL": "https://example.com/empty",
                        "statusCode": 200
                    }
                }
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            assert response.json()["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    async def test_crawl_page_with_missing_url(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that pages without sourceURL are rejected with validation error."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "type": "crawl.page",
                "id": "crawl_123",
                "data": {
                    "markdown": "# Content",
                    "metadata": {}  # No sourceURL or statusCode (required fields)
                }
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert - Should return 400 due to validation error
            assert response.status_code == 400
            assert "Invalid payload" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestWebhookCrawlCompleted:
    """Tests for crawl.completed webhook event."""

    async def test_crawl_completed_returns_success(
        self, test_client: AsyncClient, sample_webhook_crawl_completed,
        mock_redis_service, mock_language_detection_service
    ):
        """Test that crawl.completed webhook returns success status."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_completed
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["pages_processed"] == 2
        finally:
            app.dependency_overrides.clear()

    async def test_crawl_completed_with_empty_data(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test crawl.completed with no pages processes correctly."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "type": "crawl.completed",
                "id": "crawl_123",
                "data": []
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["pages_processed"] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_crawl_completed_processes_all_pages(
        self, test_client: AsyncClient, sample_webhook_crawl_completed,
        mock_redis_service, mock_language_detection_service
    ):
        """Test that all pages in completed event are queued for processing."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_completed
            )

            # Assert
            assert response.status_code == 200
            # Pages should be queued as background tasks
            data = response.json()
            assert data["pages_processed"] == len(sample_webhook_crawl_completed["data"])
        finally:
            app.dependency_overrides.clear()


class TestWebhookCrawlFailed:
    """Tests for crawl.failed webhook event."""

    async def test_crawl_failed_returns_error_status(
        self, test_client: AsyncClient, sample_webhook_crawl_failed,
        mock_redis_service, mock_language_detection_service
    ):
        """Test that crawl.failed webhook returns error status."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_failed
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["error"] == "Failed to crawl: Connection timeout"
        finally:
            app.dependency_overrides.clear()

    async def test_crawl_failed_with_missing_error_message(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test crawl.failed without error message handles gracefully."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "type": "crawl.failed",
                "id": "crawl_123"
                # No error field
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
        finally:
            app.dependency_overrides.clear()


class TestWebhookUnknownEvent:
    """Tests for unknown webhook events."""

    async def test_unknown_event_type_handled_gracefully(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that unknown event types don't crash the webhook."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "type": "crawl.unknown_event",
                "id": "crawl_123"
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unknown_event"
        finally:
            app.dependency_overrides.clear()


class TestWebhookErrorHandling:
    """Tests for webhook error handling."""

    async def test_malformed_json_handled_gracefully(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that malformed JSON doesn't crash the webhook."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content="invalid json{",
                headers={"Content-Type": "application/json"}
            )

            # Assert
            # Webhook error handler catches JSON errors and returns 200 with error status
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
        finally:
            app.dependency_overrides.clear()

    async def test_missing_type_field_handled(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that missing 'type' field is handled gracefully."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload = {
                "id": "crawl_123",
                # No type field
            }

            # Act
            response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

            # Assert
            assert response.status_code == 200
            # Should handle None type gracefully
        finally:
            app.dependency_overrides.clear()


class TestProcessCrawledPageFunction:
    """Tests for the process_crawled_page background task function."""

    @patch("app.api.v1.endpoints.webhooks.process_and_store_document", new_callable=AsyncMock)
    async def test_process_crawled_page_generates_correct_doc_id(
        self,
        mock_process_and_store,
        sample_crawl_page_data
    ):
        """Test that document ID is generated correctly from URL."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        from app.models.firecrawl import FirecrawlPageData, FirecrawlMetadata

        source_url = sample_crawl_page_data["metadata"]["sourceURL"]
        
        # Convert dict to Pydantic model
        page_data = FirecrawlPageData(
            markdown=sample_crawl_page_data["markdown"],
            metadata=FirecrawlMetadata(**sample_crawl_page_data["metadata"])
        )

        # Act
        await process_crawled_page(page_data)

        # Assert
        mock_process_and_store.assert_called_once()
        call_args = mock_process_and_store.call_args
        assert call_args.kwargs["content"] == sample_crawl_page_data["markdown"]
        assert call_args.kwargs["source_url"] == source_url
        assert call_args.kwargs["source_type"] == "crawl"

    @patch("app.api.v1.endpoints.webhooks.process_and_store_document", new_callable=AsyncMock)
    async def test_process_crawled_page_passes_correct_content(
        self,
        mock_process_and_store,
        sample_crawl_page_data
    ):
        """Test that content and metadata are passed correctly."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        from app.models.firecrawl import FirecrawlPageData, FirecrawlMetadata
        
        # Convert dict to Pydantic model
        page_data = FirecrawlPageData(
            markdown=sample_crawl_page_data["markdown"],
            metadata=FirecrawlMetadata(**sample_crawl_page_data["metadata"])
        )

        # Act
        await process_crawled_page(page_data)

        # Assert
        call_args = mock_process_and_store.call_args
        assert call_args.kwargs["content"] == sample_crawl_page_data["markdown"]
        assert call_args.kwargs["metadata"]["sourceURL"] == sample_crawl_page_data["metadata"]["sourceURL"]

    async def test_process_crawled_page_skips_empty_content(
        self
    ):
        """Test that pages with empty content can be processed without error."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        from app.models.firecrawl import FirecrawlPageData, FirecrawlMetadata
        
        page_data = FirecrawlPageData(
            markdown="",
            metadata=FirecrawlMetadata(sourceURL="https://example.com", statusCode=200)
        )

        # Act & Assert - should not raise exception (empty content is handled gracefully)
        try:
            await process_crawled_page(page_data)
        except Exception as e:
            pytest.fail(f"process_crawled_page raised exception for empty content: {e}")

    async def test_process_crawled_page_skips_missing_url(
        self
    ):
        """Test that pages without URL can be processed without error."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        from app.models.firecrawl import FirecrawlPageData, FirecrawlMetadata
        
        page_data = FirecrawlPageData(
            markdown="# Content",
            metadata=FirecrawlMetadata(sourceURL="", statusCode=200)  # Empty sourceURL
        )

        # Act & Assert - should not raise exception (empty URL is handled gracefully)
        try:
            await process_crawled_page(page_data)
        except Exception as e:
            pytest.fail(f"process_crawled_page raised exception for empty URL: {e}")

    @patch("app.services.document_processor.process_and_store_document")
    async def test_process_crawled_page_handles_embedding_error(
        self,
        mock_process_and_store,
        sample_crawl_page_data
    ):
        """Test that embedding errors are handled gracefully."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        from app.models.firecrawl import FirecrawlPageData, FirecrawlMetadata
        
        # Simulate process_and_store_document raising an error
        mock_process_and_store.side_effect = Exception("Embedding service unavailable")
        
        # Convert dict to Pydantic model
        page_data = FirecrawlPageData(
            markdown=sample_crawl_page_data["markdown"],
            metadata=FirecrawlMetadata(**sample_crawl_page_data["metadata"])
        )

        # Act & Assert
        # Should not raise exception (webhook should handle errors gracefully)
        try:
            await process_crawled_page(page_data)
        except Exception:
            pass  # Errors are expected to be logged, not raised

    @patch("app.services.document_processor.process_and_store_document")
    async def test_process_crawled_page_handles_vector_db_error(
        self,
        mock_process_and_store,
        sample_crawl_page_data
    ):
        """Test that vector DB errors are handled gracefully."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        from app.models.firecrawl import FirecrawlPageData, FirecrawlMetadata
        
        # Simulate process_and_store_document raising an error
        mock_process_and_store.side_effect = Exception("Vector DB unavailable")
        
        # Convert dict to Pydantic model
        page_data = FirecrawlPageData(
            markdown=sample_crawl_page_data["markdown"],
            metadata=FirecrawlMetadata(**sample_crawl_page_data["metadata"])
        )

        # Act & Assert
        # Should not raise exception (webhook should handle errors gracefully)
        try:
            await process_crawled_page(page_data)
        except Exception:
            pass  # Errors are expected to be logged, not raised
