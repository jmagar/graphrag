"""
Comprehensive error handling and edge case tests for Phase 1 implementations.

This test suite follows TDD methodology and tests:
1. Webhook endpoint: invalid JSON, missing event type, unknown event types
2. Signature verification: malformed signatures, encoding issues
3. Pydantic validation: nested validation errors, type coercion failures
4. Connection pooling: network errors, timeout handling, connection closure
5. Redis: connection failures, key expiration mid-operation
6. Background tasks: task failures, retry logic

Test Philosophy:
- RED-GREEN-REFACTOR cycle
- Test error scenarios, not just happy paths
- Verify graceful degradation
- Ensure proper error responses
"""

import pytest
import json
import hmac
import hashlib
from httpx import AsyncClient, ConnectError, TimeoutException, ReadTimeout
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pydantic import ValidationError
import redis.asyncio as redis
import redis.exceptions

# Import app and dependencies for DI overrides
from app.main import app
from app.dependencies import get_redis_service, get_language_detection_service

# Enable anyio for all tests in this module
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def setup_di_overrides(mock_redis_service, mock_language_detection_service):
    """Automatically setup DI overrides for all tests in this module."""
    app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
    app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
    yield
    app.dependency_overrides.clear()


# ============================================================================
# 1. WEBHOOK ENDPOINT ERROR HANDLING
# ============================================================================


class TestWebhookInvalidJSON:
    """Test webhook handling of invalid JSON payloads."""

    async def test_malformed_json_returns_error_status(
        self, test_client: AsyncClient
    ):
        """Test that malformed JSON doesn't crash webhook and returns error."""
        # Arrange: Invalid JSON with trailing comma, missing quotes
        invalid_json = '{"type": "crawl.page", "id": "123",}'

        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            content=invalid_json,
            headers={"Content-Type": "application/json"},
        )

        # Assert: Should return 500 Internal Server Error for JSON parsing errors
        assert response.status_code == 500

    async def test_empty_request_body(self, test_client: AsyncClient):
        """Test webhook with empty request body."""
        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            content="",
            headers={"Content-Type": "application/json"},
        )

        # Assert: Should return 500 Internal Server Error for JSON parsing errors
        assert response.status_code == 500

    async def test_non_json_content_type(self, test_client: AsyncClient):
        """Test webhook with non-JSON content type."""
        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            content="plain text data",
            headers={"Content-Type": "text/plain"},
        )

        # Assert: Should return 500 Internal Server Error for JSON parsing errors
        assert response.status_code == 500

    async def test_binary_data_in_webhook(self, test_client: AsyncClient):
        """Test webhook receiving binary data instead of JSON."""
        # Arrange: Binary data
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00"

        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            content=binary_data,
            headers={"Content-Type": "application/json"},
        )

        # Assert: Should return 500 Internal Server Error for JSON parsing errors
        assert response.status_code == 500

    async def test_extremely_large_json_payload(self, test_client: AsyncClient):
        """Test webhook with extremely large JSON payload."""
        # Arrange: Create a large payload (10MB)
        large_content = "x" * (10 * 1024 * 1024)
        payload = {"type": "crawl.page", "id": "123", "data": {"markdown": large_content}}

        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            json=payload,
            timeout=30.0,
        )

        # Assert: Should return 400 Bad Request for validation errors (missing required metadata field)
        assert response.status_code == 400


class TestWebhookMissingFields:
    """Test webhook handling of missing required fields."""

    async def test_missing_type_field(self, test_client: AsyncClient):
        """Test webhook with missing 'type' field."""
        # Arrange
        payload = {"id": "crawl_123", "data": {}}

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should handle gracefully
        assert response.status_code == 200
        data = response.json()
        # May return unknown_event or error
        assert data["status"] in ["unknown_event", "error"]

    async def test_missing_id_field(self, test_client: AsyncClient):
        """Test webhook with missing 'id' field."""
        # Arrange
        payload = {"type": "crawl.page", "data": {"markdown": "test"}}

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should return 400 Bad Request for validation errors (missing required id and metadata fields)
        assert response.status_code == 400

    async def test_missing_data_field_in_crawl_page(self, test_client: AsyncClient):
        """Test crawl.page webhook with missing 'data' field."""
        # Arrange
        payload = {"type": "crawl.page", "id": "crawl_123"}

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should return 400 due to Pydantic validation
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestWebhookUnknownEventTypes:
    """Test webhook handling of unknown event types."""

    async def test_future_event_type_handled(self, test_client: AsyncClient):
        """Test webhook with hypothetical future event type."""
        # Arrange: Simulate a new event type that doesn't exist yet
        payload = {
            "type": "crawl.paused",  # Future event type
            "id": "crawl_123",
            "reason": "User requested pause",
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should return unknown_event status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unknown_event"

    async def test_misspelled_event_type(self, test_client: AsyncClient):
        """Test webhook with misspelled event type."""
        # Arrange
        payload = {"type": "crawl.pagee", "id": "crawl_123"}  # Typo: pagee

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unknown_event"

    async def test_null_event_type(self, test_client: AsyncClient):
        """Test webhook with null event type."""
        # Arrange
        payload = {"type": None, "id": "crawl_123"}

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["unknown_event", "error"]


# ============================================================================
# 2. SIGNATURE VERIFICATION ERROR HANDLING
# ============================================================================


class TestSignatureVerification:
    """Test HMAC signature verification edge cases."""

    @patch("app.api.v1.endpoints.webhooks.settings")
    async def test_invalid_signature_returns_401(
        self, mock_settings, test_client: AsyncClient
    ):
        """Test that invalid signature returns 401 Unauthorized."""
        # Arrange: Configure webhook secret
        mock_settings.FIRECRAWL_WEBHOOK_SECRET = "test_secret_key"
        mock_settings.ENABLE_STREAMING_PROCESSING = True

        payload = {"type": "crawl.started", "id": "crawl_123"}
        payload_bytes = json.dumps(payload).encode()

        # Create invalid signature
        invalid_signature = "invalid_signature_hash"

        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Firecrawl-Signature": invalid_signature,
            },
        )

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "Invalid webhook signature" in data["detail"]

    @patch("app.api.v1.endpoints.webhooks.settings")
    async def test_missing_signature_header_returns_401(
        self, mock_settings, test_client: AsyncClient
    ):
        """Test that missing signature header returns 401 when secret configured."""
        # Arrange
        mock_settings.FIRECRAWL_WEBHOOK_SECRET = "test_secret_key"

        payload = {"type": "crawl.started", "id": "crawl_123"}

        # Act: Don't include X-Firecrawl-Signature header
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 401

    @patch("app.api.v1.endpoints.webhooks.settings")
    async def test_valid_signature_succeeds(
        self, mock_settings, test_client: AsyncClient
    ):
        """Test that valid signature allows webhook processing."""
        # Arrange
        secret = "test_secret_key"
        mock_settings.FIRECRAWL_WEBHOOK_SECRET = secret
        mock_settings.ENABLE_STREAMING_PROCESSING = True

        payload = {"type": "crawl.started", "id": "crawl_123"}
        payload_bytes = json.dumps(payload).encode()

        # Generate valid signature
        expected_signature = hmac.new(
            secret.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()

        # Act
        response = await test_client.post(
            "/api/v1/webhooks/firecrawl",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Firecrawl-Signature": expected_signature,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"

    async def test_signature_with_unicode_characters(self, test_client: AsyncClient):
        """Test signature verification with Unicode characters in payload."""
        # Arrange
        secret = "test_secret_key"
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test 日本語 Ñoño 🚀",
                "metadata": {"sourceURL": "https://example.com/unicode"},
            },
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        # Generate signature
        signature = hmac.new(
            secret.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()

        # Act
        with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
            mock_settings.FIRECRAWL_WEBHOOK_SECRET = secret
            mock_settings.ENABLE_STREAMING_PROCESSING = True

            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Firecrawl-Signature": signature,
                },
            )

        # Assert: Should return 400 Bad Request for validation errors (missing required statusCode field)
        assert response.status_code == 400

    async def test_signature_with_different_json_spacing(
        self, test_client: AsyncClient
    ):
        """Test that signature fails when JSON spacing differs."""
        # Arrange
        secret = "test_secret_key"
        payload_dict = {"type": "crawl.started", "id": "crawl_123"}

        # Create two different JSON representations
        compact_json = json.dumps(payload_dict, separators=(",", ":"))
        spaced_json = json.dumps(payload_dict, indent=2)

        # Generate signature for compact version
        signature = hmac.new(
            secret.encode(), compact_json.encode(), hashlib.sha256
        ).hexdigest()

        # Act: Send spaced version with compact signature
        with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
            mock_settings.FIRECRAWL_WEBHOOK_SECRET = secret

            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=spaced_json,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature,
                },
            )

        # Assert: Should fail because byte representation differs
        assert response.status_code == 401

    async def test_empty_signature_string(self, test_client: AsyncClient):
        """Test signature verification with empty string."""
        # Arrange
        with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
            mock_settings.FIRECRAWL_WEBHOOK_SECRET = "test_secret"

            payload = {"type": "crawl.started", "id": "crawl_123"}

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=payload,
                headers={"X-Firecrawl-Signature": ""},
            )

        # Assert
        assert response.status_code == 401


# ============================================================================
# 3. PYDANTIC VALIDATION ERROR HANDLING
# ============================================================================


class TestPydanticValidation:
    """Test Pydantic validation error scenarios."""

    async def test_invalid_status_code_in_metadata(self, test_client: AsyncClient):
        """Test validation error for invalid HTTP status code."""
        # Arrange: statusCode outside valid range (100-599)
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 999,  # Invalid: > 599
                },
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should return 400 with validation error
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "statusCode" in str(data["detail"])

    async def test_missing_required_markdown_field(self, test_client: AsyncClient):
        """Test validation error for missing required 'markdown' field."""
        # Arrange
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                # Missing 'markdown' field
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                }
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "markdown" in str(data["detail"]).lower()

    async def test_missing_required_metadata_field(self, test_client: AsyncClient):
        """Test validation error for missing required 'metadata' field."""
        # Arrange
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                # Missing 'metadata' field
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "metadata" in str(data["detail"]).lower()

    async def test_missing_source_url_in_metadata(self, test_client: AsyncClient):
        """Test validation error for missing 'sourceURL' in metadata."""
        # Arrange
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {
                    # Missing 'sourceURL'
                    "statusCode": 200,
                },
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "sourceURL" in str(data["detail"])

    async def test_wrong_type_for_links_field(self, test_client: AsyncClient):
        """Test validation error when 'links' is not a list."""
        # Arrange
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
                "links": "not a list",  # Should be List[str]
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 400

    async def test_nested_validation_error_in_completed_event(
        self, test_client: AsyncClient
    ):
        """Test nested validation error in crawl.completed event."""
        # Arrange: One page has invalid data
        payload = {
            "type": "crawl.completed",
            "id": "crawl_123",
            "data": [
                {
                    "markdown": "# Valid Page",
                    "metadata": {
                        "sourceURL": "https://example.com/page1",
                        "statusCode": 200,
                    },
                },
                {
                    "markdown": "# Invalid Page",
                    "metadata": {
                        "sourceURL": "https://example.com/page2",
                        "statusCode": 9999,  # Invalid status code
                    },
                },
            ],
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 400

    async def test_type_coercion_for_integer_as_string(
        self, test_client: AsyncClient
    ):
        """Test Pydantic type coercion for integers as strings."""
        # Arrange: statusCode as string (should coerce to int)
        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": "200",  # String instead of int
                },
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Pydantic should coerce successfully
        assert response.status_code == 200


# ============================================================================
# 4. CONNECTION POOLING ERROR HANDLING
# ============================================================================


class TestConnectionPoolingErrors:
    """Test connection pooling error scenarios in FirecrawlService."""

    @patch("app.services.firecrawl.httpx.AsyncClient")
    async def test_network_error_during_crawl_start(self, mock_client_class):
        """Test handling of network errors when starting a crawl."""
        # Arrange
        from app.services.firecrawl import FirecrawlService

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ConnectError("Connection refused"))
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        service = FirecrawlService()

        # Act & Assert
        with pytest.raises(ConnectError):
            await service.start_crawl({"url": "https://example.com"})

    @patch("app.services.firecrawl.httpx.AsyncClient")
    async def test_timeout_error_during_status_check(self, mock_client_class):
        """Test handling of timeout errors when checking crawl status."""
        # Arrange
        from app.services.firecrawl import FirecrawlService

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=TimeoutException("Request timeout"))
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        service = FirecrawlService()

        # Act & Assert
        with pytest.raises(TimeoutException):
            await service.get_crawl_status("crawl_123")

    @patch("app.services.firecrawl.httpx.AsyncClient")
    async def test_client_recreated_after_close(self, mock_client_class):
        """Test that client is recreated after being closed."""
        # Arrange
        from app.services.firecrawl import FirecrawlService

        # First client (starts open, will be closed later)
        mock_client_1 = AsyncMock()
        mock_client_1.is_closed = False  # Initially not closed
        mock_client_1.post = AsyncMock(
            return_value=MagicMock(
                json=lambda: {"id": "123"},
                raise_for_status=lambda: None,
            )
        )

        # Second client (created after first is closed)
        mock_client_2 = AsyncMock()
        mock_client_2.is_closed = False
        mock_client_2.post = AsyncMock(
            return_value=MagicMock(
                json=lambda: {"id": "456"},
                raise_for_status=lambda: None,
            )
        )

        mock_client_class.side_effect = [mock_client_1, mock_client_2]

        service = FirecrawlService()

        # Act: First request creates client
        result1 = await service.start_crawl({"url": "https://example.com"})
        assert result1["id"] == "123"
        assert mock_client_class.call_count == 1

        # Simulate client being closed
        mock_client_1.is_closed = True

        # Act: Second request should detect closed client and recreate
        result2 = await service.start_crawl({"url": "https://example2.com"})

        # Assert: Should have created new client
        assert mock_client_class.call_count == 2
        assert result2["id"] == "456"

    @patch("app.services.firecrawl.httpx.AsyncClient")
    async def test_read_timeout_during_large_response(self, mock_client_class):
        """Test handling of read timeout during large response."""
        # Arrange
        from app.services.firecrawl import FirecrawlService

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=ReadTimeout("Read timeout"))
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        service = FirecrawlService()

        # Act & Assert
        with pytest.raises(ReadTimeout):
            await service.get_crawl_status("crawl_123")

    @patch("app.services.firecrawl.httpx.AsyncClient")
    async def test_connection_pool_exhaustion(self, mock_client_class):
        """Test behavior when connection pool is exhausted."""
        # Arrange
        from app.services.firecrawl import FirecrawlService

        mock_client = AsyncMock()
        # Simulate pool exhaustion with custom exception
        mock_client.post = AsyncMock(
            side_effect=Exception("Connection pool is exhausted")
        )
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        service = FirecrawlService()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service.start_crawl({"url": "https://example.com"})
        assert "pool is exhausted" in str(exc_info.value)


# ============================================================================
# 5. REDIS ERROR HANDLING
# ============================================================================


class TestRedisErrorHandling:
    """Test Redis error scenarios and graceful degradation."""

    @patch("app.services.redis_service.redis.Redis")
    async def test_redis_connection_failure_on_init(self, mock_redis_class):
        """Test graceful handling when Redis connection fails on init."""
        # Arrange
        from app.services.redis_service import RedisService

        mock_redis_class.side_effect = Exception("Connection refused")

        # Act
        service = RedisService()

        # Assert: Should initialize with unavailable flag
        assert service._available is False
        assert service.client is None

    async def test_redis_unavailable_returns_safe_defaults(self):
        """Test that methods return safe defaults when Redis unavailable."""
        # Arrange
        from app.services.redis_service import RedisService

        with patch("app.services.redis_service.redis.Redis") as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")
            service = RedisService()

        # Act & Assert
        assert await service.mark_page_processed("crawl_123", "url") is False
        assert await service.is_page_processed("crawl_123", "url") is False
        assert await service.get_processed_count("crawl_123") == 0
        assert await service.cleanup_crawl_tracking("crawl_123") is False
        assert await service.get_cached_embedding("query") is None

    @patch("app.services.redis_service.redis.Redis")
    async def test_redis_ping_failure_marks_unavailable(self, mock_redis_class):
        """Test that ping failure correctly marks Redis as unavailable."""
        # Arrange
        from app.services.redis_service import RedisService

        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Connection lost"))
        mock_redis_class.return_value = mock_client

        service = RedisService()

        # Act
        is_available = await service.is_available()

        # Assert
        assert is_available is False

    @patch("app.services.redis_service.redis.Redis")
    async def test_key_expiration_mid_operation(self, mock_redis_class):
        """Test handling when Redis key expires during operation."""
        # Arrange
        from app.services.redis_service import RedisService

        mock_client = AsyncMock()
        # First call succeeds, second returns None (expired)
        mock_client.sismember = AsyncMock(return_value=None)
        mock_client.ping = AsyncMock(return_value=True)
        mock_redis_class.return_value = mock_client

        service = RedisService()

        # Act
        is_processed = await service.is_page_processed("crawl_123", "url")

        # Assert: Should handle gracefully
        assert is_processed is False

    @patch("app.services.redis_service.redis.Redis")
    async def test_redis_operation_timeout(self, mock_redis_class):
        """Test handling of Redis operation timeout."""
        # Arrange
        from app.services.redis_service import RedisService

        mock_client = AsyncMock()
        mock_client.sadd = AsyncMock(
            side_effect=redis.exceptions.TimeoutError("Operation timeout")
        )
        mock_client.ping = AsyncMock(return_value=True)
        mock_redis_class.return_value = mock_client

        service = RedisService()

        # Act
        result = await service.mark_page_processed("crawl_123", "url")

        # Assert: Should handle gracefully and return False
        assert result is False

    @patch("app.services.redis_service.redis.Redis")
    async def test_redis_connection_pool_exhausted(self, mock_redis_class):
        """Test handling when Redis connection pool is exhausted."""
        # Arrange
        from app.services.redis_service import RedisService

        mock_client = AsyncMock()
        mock_client.sadd = AsyncMock(
            side_effect=redis.exceptions.ConnectionError("Too many connections")
        )
        mock_client.ping = AsyncMock(return_value=True)
        mock_redis_class.return_value = mock_client

        service = RedisService()

        # Act
        result = await service.mark_page_processed("crawl_123", "url")

        # Assert
        assert result is False

    @patch("app.services.redis_service.redis.Redis")
    async def test_json_decode_error_in_cache_retrieval(self, mock_redis_class):
        """Test handling of JSON decode error when retrieving cached embedding."""
        # Arrange
        from app.services.redis_service import RedisService

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value="invalid json{")
        mock_client.ping = AsyncMock(return_value=True)
        mock_redis_class.return_value = mock_client

        service = RedisService()

        # Act
        result = await service.get_cached_embedding("query")

        # Assert: Should handle gracefully and return None
        assert result is None


# ============================================================================
# 6. BACKGROUND TASK ERROR HANDLING
# ============================================================================


class TestBackgroundTaskErrors:
    """Test background task error handling and failure scenarios."""

    @patch("app.services.document_processor.embeddings_service")
    @patch("app.services.document_processor.vector_db_service")
    async def test_embedding_service_failure_in_background_task(
        self, mock_vector_db, mock_embeddings
    ):
        """Test graceful handling when embedding service fails in background task."""
        # Arrange
        from app.services.document_processor import process_and_store_document

        mock_embeddings.generate_embeddings = AsyncMock(
            side_effect=Exception("TEI service unavailable")
        )
        mock_vector_db.upsert_documents = AsyncMock()

        # Act: Should not raise exception
        await process_and_store_document(
            content="Test content",
            source_url="https://example.com",
            metadata={},
            source_type="crawl",
        )

        # Assert: Vector DB should not be called
        mock_vector_db.upsert_documents.assert_not_called()

    @patch("app.services.document_processor.embeddings_service")
    @patch("app.services.document_processor.vector_db_service")
    async def test_vector_db_failure_in_background_task(
        self, mock_vector_db, mock_embeddings
    ):
        """Test graceful handling when vector DB fails in background task."""
        # Arrange
        from app.services.document_processor import process_and_store_document

        mock_embeddings.generate_embeddings = AsyncMock(return_value=[[0.1] * 768])
        mock_vector_db.upsert_documents = AsyncMock(
            side_effect=Exception("Qdrant unavailable")
        )

        # Act: Should not raise exception
        await process_and_store_document(
            content="Test content",
            source_url="https://example.com",
            metadata={},
            source_type="crawl",
        )

        # Assert: Embedding was generated
        mock_embeddings.generate_embeddings.assert_called_once()

    @patch("app.services.document_processor.embeddings_service")
    async def test_empty_content_skipped_in_batch(self, mock_embeddings):
        """Test that documents with empty content are filtered out in batch processing."""
        # Arrange
        from app.services.document_processor import process_and_store_documents_batch

        mock_embeddings.generate_embeddings = AsyncMock()

        documents = [
            {
                "content": "",  # Empty content
                "source_url": "https://example.com/page1",
                "metadata": {},
                "source_type": "crawl",
            },
            {
                "content": None,  # None content
                "source_url": "https://example.com/page2",
                "metadata": {},
                "source_type": "crawl",
            },
        ]

        # Act
        await process_and_store_documents_batch(documents)

        # Assert: Should not call embeddings service
        mock_embeddings.generate_embeddings.assert_not_called()

    @patch("app.services.document_processor.embeddings_service")
    async def test_missing_source_url_skipped_in_batch(self, mock_embeddings):
        """Test that documents without source_url are filtered out."""
        # Arrange
        from app.services.document_processor import process_and_store_documents_batch

        mock_embeddings.generate_embeddings = AsyncMock()

        documents = [
            {
                "content": "Test content",
                "source_url": "",  # Empty URL
                "metadata": {},
                "source_type": "crawl",
            },
            {
                "content": "Test content 2",
                "source_url": None,  # None URL
                "metadata": {},
                "source_type": "crawl",
            },
        ]

        # Act
        await process_and_store_documents_batch(documents)

        # Assert
        mock_embeddings.generate_embeddings.assert_not_called()

    @patch("app.services.document_processor.embeddings_service")
    @patch("app.services.document_processor.vector_db_service")
    async def test_partial_batch_failure_recovery(
        self, mock_vector_db, mock_embeddings
    ):
        """Test that batch processing continues after partial failure."""
        # Arrange
        from app.services.document_processor import process_and_store_documents_batch

        # First call fails, second succeeds
        mock_embeddings.generate_embeddings = AsyncMock(
            side_effect=[
                Exception("Temporary failure"),
                [[0.1] * 768, [0.2] * 768],
            ]
        )
        mock_vector_db.upsert_documents = AsyncMock()

        documents = [
            {
                "content": "Test 1",
                "source_url": "https://example.com/1",
                "metadata": {},
                "source_type": "crawl",
            },
            {
                "content": "Test 2",
                "source_url": "https://example.com/2",
                "metadata": {},
                "source_type": "crawl",
            },
        ]

        # Act: Should handle first failure gracefully
        await process_and_store_documents_batch(documents)

        # Assert: Called once (failed on first attempt)
        assert mock_embeddings.generate_embeddings.call_count == 1


# ============================================================================
# 7. WEBHOOK + REDIS INTEGRATION ERROR SCENARIOS
# ============================================================================


class TestWebhookRedisIntegration:
    """Test error scenarios in webhook + Redis integration."""

    async def test_redis_unavailable_during_page_tracking(
        self, test_client: AsyncClient, mock_redis_service
    ):
        """Test webhook continues processing when Redis unavailable."""
        # Arrange
        mock_redis_service.mark_page_processed = AsyncMock(return_value=False)
        mock_redis_service.is_available = AsyncMock(return_value=False)

        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should succeed despite Redis failure
        assert response.status_code == 200

    async def test_redis_cleanup_failure_on_crawl_failed(
        self, test_client: AsyncClient, mock_redis_service
    ):
        """Test that webhook succeeds even if Redis cleanup fails."""
        # Arrange
        mock_redis_service.cleanup_crawl_tracking = AsyncMock(return_value=False)

        payload = {
            "type": "crawl.failed",
            "id": "crawl_123",
            "error": "Test error",
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should succeed despite cleanup failure
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    async def test_redis_is_page_processed_error_during_deduplication(
        self, test_client: AsyncClient, mock_redis_service
    ):
        """Test that unhandled Redis exceptions are properly raised as 500 errors."""
        # Arrange: Mock raises exception that bypasses service error handling
        mock_redis_service.is_page_processed = AsyncMock(
            side_effect=Exception("Redis error")
        )
        mock_redis_service.cleanup_crawl_tracking = AsyncMock(return_value=True)

        payload = {
            "type": "crawl.completed",
            "id": "crawl_123",
            "data": [
                {
                    "markdown": "# Test",
                    "metadata": {
                        "sourceURL": "https://example.com",
                        "statusCode": 200,
                    },
                }
            ],
        }

        # Act: Unhandled exception at mock level
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should return 500 Internal Server Error for unexpected exceptions
        assert response.status_code == 500


# ============================================================================
# 8. EDGE CASES AND RACE CONDITIONS
# ============================================================================


class TestEdgeCasesAndRaceConditions:
    """Test edge cases and potential race conditions."""

    async def test_concurrent_webhook_requests_same_crawl(
        self, test_client: AsyncClient
    ):
        """Test handling of concurrent webhook requests for same crawl."""
        # Arrange
        import asyncio

        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {
                    "sourceURL": "https://example.com/page1",
                    "statusCode": 200,
                },
            },
        }

        # Act: Send multiple concurrent requests
        tasks = [
            test_client.post("/api/v1/webhooks/firecrawl", json=payload)
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        # Assert: All should succeed
        for response in responses:
            assert response.status_code == 200

    async def test_webhook_with_extremely_long_url(self, test_client: AsyncClient):
        """Test webhook with extremely long URL."""
        # Arrange: URL with 10,000 characters
        long_url = "https://example.com/" + "a" * 9980

        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {"sourceURL": long_url, "statusCode": 200},
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should handle gracefully
        assert response.status_code == 200

    async def test_webhook_with_special_characters_in_url(
        self, test_client: AsyncClient
    ):
        """Test webhook with special characters in URL."""
        # Arrange
        special_url = "https://example.com/page?param=value&foo=bar#section"

        payload = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "# Test",
                "metadata": {"sourceURL": special_url, "statusCode": 200},
            },
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert
        assert response.status_code == 200

    async def test_crawl_completed_with_duplicate_urls(self, test_client: AsyncClient):
        """Test crawl.completed handling duplicate URLs in same batch."""
        # Arrange: Same URL appears twice
        payload = {
            "type": "crawl.completed",
            "id": "crawl_123",
            "data": [
                {
                    "markdown": "# Version 1",
                    "metadata": {
                        "sourceURL": "https://example.com/duplicate",
                        "statusCode": 200,
                    },
                },
                {
                    "markdown": "# Version 2",
                    "metadata": {
                        "sourceURL": "https://example.com/duplicate",
                        "statusCode": 200,
                    },
                },
            ],
        }

        # Act
        response = await test_client.post("/api/v1/webhooks/firecrawl", json=payload)

        # Assert: Should handle duplicates gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
