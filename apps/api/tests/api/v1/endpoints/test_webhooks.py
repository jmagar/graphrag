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

# Enable anyio for all tests in this module
pytestmark = pytest.mark.anyio


class TestWebhookCrawlStarted:
    """Tests for crawl.started webhook event."""

    async def test_crawl_started_returns_acknowledged(
        self, test_client: AsyncClient
    ):
        """Test that crawl.started webhook is acknowledged."""
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

    async def test_crawl_started_with_missing_id(
        self, test_client: AsyncClient
    ):
        """Test crawl.started webhook with missing ID still responds."""
        # Arrange
        payload = {"type": "crawl.started"}

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"


class TestWebhookCrawlPage:
    """Tests for crawl.page webhook event."""

    async def test_crawl_page_triggers_background_processing(
        self, test_client: AsyncClient, sample_webhook_crawl_page
    ):
        """Test that crawl.page webhook triggers background processing."""
        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            json=sample_webhook_crawl_page
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    @patch("app.api.v1.endpoints.webhooks.vector_db_service")
    async def test_crawl_page_processes_content_correctly(
        self,
        mock_vector_db,
        mock_embeddings,
        test_client: AsyncClient,
        sample_webhook_crawl_page
    ):
        """Test that page content is processed and stored correctly."""
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

    async def test_crawl_page_with_empty_content(
        self, test_client: AsyncClient
    ):
        """Test that pages with empty content are handled gracefully."""
        # Arrange
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "",
                "metadata": {"sourceURL": "https://example.com/empty"}
            }
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "processing"

    async def test_crawl_page_with_missing_url(
        self, test_client: AsyncClient
    ):
        """Test that pages without sourceURL are handled gracefully."""
        # Arrange
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Content",
                "metadata": {}  # No sourceURL
            }
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "processing"


class TestWebhookCrawlCompleted:
    """Tests for crawl.completed webhook event."""

    async def test_crawl_completed_returns_success(
        self, test_client: AsyncClient, sample_webhook_crawl_completed
    ):
        """Test that crawl.completed webhook returns success status."""
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

    async def test_crawl_completed_with_empty_data(
        self, test_client: AsyncClient
    ):
        """Test crawl.completed with no pages processes correctly."""
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

    async def test_crawl_completed_processes_all_pages(
        self, test_client: AsyncClient, sample_webhook_crawl_completed
    ):
        """Test that all pages in completed event are queued for processing."""
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


class TestWebhookCrawlFailed:
    """Tests for crawl.failed webhook event."""

    async def test_crawl_failed_returns_error_status(
        self, test_client: AsyncClient, sample_webhook_crawl_failed
    ):
        """Test that crawl.failed webhook returns error status."""
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

    async def test_crawl_failed_with_missing_error_message(
        self, test_client: AsyncClient
    ):
        """Test crawl.failed without error message handles gracefully."""
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


class TestWebhookUnknownEvent:
    """Tests for unknown webhook events."""

    async def test_unknown_event_type_handled_gracefully(
        self, test_client: AsyncClient
    ):
        """Test that unknown event types don't crash the webhook."""
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


class TestWebhookErrorHandling:
    """Tests for webhook error handling."""

    async def test_malformed_json_handled_gracefully(
        self, test_client: AsyncClient
    ):
        """Test that malformed JSON doesn't crash the webhook."""
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

    async def test_missing_type_field_handled(
        self, test_client: AsyncClient
    ):
        """Test that missing 'type' field is handled gracefully."""
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


class TestProcessCrawledPageFunction:
    """Tests for the process_crawled_page background task function."""

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    @patch("app.api.v1.endpoints.webhooks.vector_db_service")
    async def test_process_crawled_page_generates_correct_doc_id(
        self,
        mock_vector_db,
        mock_embeddings,
        sample_crawl_page_data
    ):
        """Test that document ID is generated correctly from URL."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        
        mock_embeddings.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_vector_db.upsert_document = AsyncMock()

        source_url = sample_crawl_page_data["metadata"]["sourceURL"]
        expected_doc_id = hashlib.md5(source_url.encode()).hexdigest()

        # Act
        await process_crawled_page(sample_crawl_page_data)

        # Assert
        mock_embeddings.generate_embedding.assert_called_once()
        mock_vector_db.upsert_document.assert_called_once()
        
        # Check the doc_id passed to upsert_document
        call_args = mock_vector_db.upsert_document.call_args
        assert call_args.kwargs["doc_id"] == expected_doc_id

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    @patch("app.api.v1.endpoints.webhooks.vector_db_service")
    async def test_process_crawled_page_passes_correct_content(
        self,
        mock_vector_db,
        mock_embeddings,
        sample_crawl_page_data
    ):
        """Test that content and metadata are passed correctly."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        
        mock_embeddings.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_vector_db.upsert_document = AsyncMock()

        # Act
        await process_crawled_page(sample_crawl_page_data)

        # Assert
        call_args = mock_vector_db.upsert_document.call_args
        assert call_args.kwargs["content"] == sample_crawl_page_data["markdown"]
        assert call_args.kwargs["metadata"] == sample_crawl_page_data["metadata"]

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    async def test_process_crawled_page_skips_empty_content(
        self,
        mock_embeddings
    ):
        """Test that pages with empty content are skipped."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        
        mock_embeddings.generate_embedding = AsyncMock()
        page_data = {
            "markdown": "",
            "metadata": {"sourceURL": "https://example.com"}
        }

        # Act
        await process_crawled_page(page_data)

        # Assert
        mock_embeddings.generate_embedding.assert_not_called()

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    async def test_process_crawled_page_skips_missing_url(
        self,
        mock_embeddings
    ):
        """Test that pages without URL are skipped."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        
        mock_embeddings.generate_embedding = AsyncMock()
        page_data = {
            "markdown": "# Content",
            "metadata": {}  # No sourceURL
        }

        # Act
        await process_crawled_page(page_data)

        # Assert
        mock_embeddings.generate_embedding.assert_not_called()

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    @patch("app.api.v1.endpoints.webhooks.vector_db_service")
    async def test_process_crawled_page_handles_embedding_error(
        self,
        mock_vector_db,
        mock_embeddings,
        sample_crawl_page_data
    ):
        """Test that embedding errors are handled gracefully."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        
        mock_embeddings.generate_embedding = AsyncMock(
            side_effect=Exception("Embedding service unavailable")
        )
        mock_vector_db.upsert_document = AsyncMock()

        # Act & Assert
        # Should not raise exception
        await process_crawled_page(sample_crawl_page_data)
        
        # Vector DB should not be called if embedding fails
        mock_vector_db.upsert_document.assert_not_called()

    @patch("app.api.v1.endpoints.webhooks.embeddings_service")
    @patch("app.api.v1.endpoints.webhooks.vector_db_service")
    async def test_process_crawled_page_handles_vector_db_error(
        self,
        mock_vector_db,
        mock_embeddings,
        sample_crawl_page_data
    ):
        """Test that vector DB errors are handled gracefully."""
        # Arrange
        from app.api.v1.endpoints.webhooks import process_crawled_page
        
        mock_embeddings.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_vector_db.upsert_document = AsyncMock(
            side_effect=Exception("Vector DB unavailable")
        )

        # Act & Assert
        # Should not raise exception
        await process_crawled_page(sample_crawl_page_data)
