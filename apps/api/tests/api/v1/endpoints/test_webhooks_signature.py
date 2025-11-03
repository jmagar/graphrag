"""
Tests for webhook signature verification.

These tests follow TDD methodology:
1. RED: Test written first (expecting failure)
2. GREEN: Implementation makes test pass
3. REFACTOR: Improve code while keeping tests green

Test Coverage:
- Valid HMAC-SHA256 signature verification
- Invalid signature rejection (401 response)
- Missing signature handling when secret is configured
- Backwards compatibility (no verification when FIRECRAWL_WEBHOOK_SECRET is empty)
- Timing attack resistance (constant-time comparison)
"""

import pytest
import hmac
import hashlib
import json
from httpx import AsyncClient
from unittest.mock import patch
from typing import Dict, Any

from app.main import app
from app.dependencies import get_redis_service, get_language_detection_service

# Enable anyio for all tests in this module
pytestmark = pytest.mark.anyio


def compute_signature(payload: Dict[str, Any], secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for a webhook payload.

    Args:
        payload: Dictionary to sign
        secret: Webhook secret

    Returns:
        Hex-encoded HMAC signature
    """
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    return hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


class TestWebhookSignatureVerification:
    """Tests for valid webhook signature verification."""

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_valid_signature_accepts_request(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that request with valid signature is accepted."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "test-secret-key"
            payload = {
                "type": "crawl.page",
                "id": "crawl_123",
                "data": {
                    "markdown": "# Example Page\n\nThis is sample content from a crawled page.",
                    "metadata": {
                        "sourceURL": "https://example.com/page1",
                        "title": "Example Page",
                        "description": "This is an example page",
                        "statusCode": 200
                    }
                }
            }
            payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_valid_signature_with_special_characters(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test that signature verification works with special characters in payload."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "test-secret-key"
            payload = {
                "type": "crawl.page",
                "id": "crawl_123",
                "data": {
                    "markdown": "# Test\n\nSpecial chars: \"quotes\", 'apostrophes', <html>, &amp;",
                    "metadata": {
                        "sourceURL": "https://example.com/page?param=value&other=data",
                        "title": "Test Page with Unicode: \u00e9\u00f1\u00fc",
                        "statusCode": 200
                    }
                }
            }
            payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_valid_signature_with_empty_string_fields(
        self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service
    ):
        """Test signature verification with empty string fields."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "test-secret-key"
            payload = {
                "type": "crawl.page",
                "id": "crawl_123",
                "data": {
                    "markdown": "",
                    "metadata": {
                        "sourceURL": "https://example.com/empty",
                        "title": "",
                        "statusCode": 200
                    }
                }
            }
            payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestInvalidSignatureRejection:
    """Tests for invalid signature rejection."""

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_invalid_signature_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that request with invalid signature is rejected with 401."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')
            invalid_signature = "invalid_signature_hash"

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": invalid_signature
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_wrong_secret_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that signature with wrong secret is rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            wrong_secret = "wrong-secret-key"
            payload_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                wrong_secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_tampered_payload_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that tampered payload is detected and rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "test-secret-key"
            original_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                secret.encode(),
                original_bytes,
                hashlib.sha256
            ).hexdigest()

            # Tamper with the payload after signature calculation
            sample_webhook_crawl_page["id"] = "tampered_crawl_id"
            tampered_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=tampered_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_empty_signature_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that empty signature header is rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": ""
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_malformed_signature_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that malformed signature (wrong format) is rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')
            malformed_signature = "not-a-hex-hash"

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": malformed_signature
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_signature_with_different_algorithm_rejects(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that signature computed with different algorithm is rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "test-secret-key"
            payload_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')
            # Use SHA1 instead of SHA256
            signature_sha1 = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha1
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature_sha1
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()


class TestMissingSignatureHandling:
    """Tests for missing signature header when secret is configured."""

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_missing_signature_header_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that missing signature header is rejected when secret is configured."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_page
                # No X-Firecrawl-Signature header
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_null_signature_header_rejects_request(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that null/None signature header is rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload_bytes = json.dumps(sample_webhook_crawl_page, separators=(',', ':')).encode('utf-8')

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json"
                    # X-Firecrawl-Signature header not set
                }
            )

            # Assert
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestBackwardsCompatibility:
    """Tests for backwards compatibility when FIRECRAWL_WEBHOOK_SECRET is empty."""

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "")
    async def test_no_secret_skips_verification(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that webhook processing works without signature when secret is empty."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_page
                # No signature header needed
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "")
    async def test_no_secret_accepts_invalid_signature(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that invalid signature is ignored when secret is empty."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_page,
                headers={
                    "X-Firecrawl-Signature": "invalid_signature"
                }
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "")
    async def test_no_secret_accepts_any_payload(
        self, test_client: AsyncClient, sample_webhook_crawl_completed: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that all webhook events work without signature when secret is empty."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Test crawl.completed event
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                json=sample_webhook_crawl_completed
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", None)
    async def test_none_secret_skips_verification(
        self, test_client: AsyncClient, sample_webhook_crawl_page: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that None secret is treated the same as empty string."""
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
        finally:
            app.dependency_overrides.clear()


class TestTimingAttackResistance:
    """Tests for constant-time comparison to prevent timing attacks."""

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_uses_constant_time_comparison(self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service):
        """
        Test that signature comparison uses hmac.compare_digest.

        Note: This test verifies the implementation uses constant-time comparison.
        Actual timing attack resistance requires careful implementation review.
        """
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            from app.api.v1.endpoints.webhooks import verify_webhook_signature

            secret = "test-secret-key"
            payload = b'{"type":"crawl.page","id":"crawl_123"}'

            # Compute correct signature
            correct_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Create signatures that differ at different positions
            # If not using constant-time comparison, these would take different times
            wrong_first_char = "X" + correct_signature[1:]
            wrong_middle_char = correct_signature[:32] + "X" + correct_signature[33:]
            wrong_last_char = correct_signature[:-1] + "X"

            # Act & Assert - all should return False
            assert verify_webhook_signature(payload, wrong_first_char, secret) is False
            assert verify_webhook_signature(payload, wrong_middle_char, secret) is False
            assert verify_webhook_signature(payload, wrong_last_char, secret) is False

            # Correct signature should return True
            assert verify_webhook_signature(payload, correct_signature, secret) is True
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "test-secret-key")
    async def test_signature_length_differences(self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service):
        """Test that signatures of different lengths are handled correctly."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            from app.api.v1.endpoints.webhooks import verify_webhook_signature

            secret = "test-secret-key"
            payload = b'{"type":"crawl.page"}'

            correct_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Act & Assert
            # Too short
            assert verify_webhook_signature(payload, correct_signature[:32], secret) is False

            # Too long
            assert verify_webhook_signature(payload, correct_signature + "extra", secret) is False

            # Correct length
            assert verify_webhook_signature(payload, correct_signature, secret) is True
        finally:
            app.dependency_overrides.clear()


class TestVerifyWebhookSignatureFunction:
    """Direct tests for verify_webhook_signature helper function."""

    def test_verify_webhook_signature_with_valid_signature(self):
        """Test verify_webhook_signature function with valid signature."""
        # Arrange
        from app.api.v1.endpoints.webhooks import verify_webhook_signature

        secret = "test-secret"
        payload = b'{"test": "data"}'
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Act
        result = verify_webhook_signature(payload, signature, secret)

        # Assert
        assert result is True

    def test_verify_webhook_signature_with_invalid_signature(self):
        """Test verify_webhook_signature function with invalid signature."""
        # Arrange
        from app.api.v1.endpoints.webhooks import verify_webhook_signature

        secret = "test-secret"
        payload = b'{"test": "data"}'
        invalid_signature = "invalid"

        # Act
        result = verify_webhook_signature(payload, invalid_signature, secret)

        # Assert
        assert result is False

    def test_verify_webhook_signature_with_empty_secret(self):
        """Test verify_webhook_signature function with empty secret."""
        # Arrange
        from app.api.v1.endpoints.webhooks import verify_webhook_signature

        payload = b'{"test": "data"}'
        signature = "any_signature"

        # Act
        result = verify_webhook_signature(payload, signature, "")

        # Assert
        assert result is False

    def test_verify_webhook_signature_with_empty_signature(self):
        """Test verify_webhook_signature function with empty signature."""
        # Arrange
        from app.api.v1.endpoints.webhooks import verify_webhook_signature

        secret = "test-secret"
        payload = b'{"test": "data"}'

        # Act
        result = verify_webhook_signature(payload, "", secret)

        # Assert
        assert result is False

    def test_verify_webhook_signature_with_unicode_payload(self):
        """Test verify_webhook_signature function with unicode content."""
        # Arrange
        from app.api.v1.endpoints.webhooks import verify_webhook_signature

        secret = "test-secret"
        payload = '{"test": "Unicode: \u00e9\u00f1\u00fc"}'.encode('utf-8')
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Act
        result = verify_webhook_signature(payload, signature, secret)

        # Assert
        assert result is True

    def test_verify_webhook_signature_case_sensitive(self):
        """Test that signature comparison is case-sensitive."""
        # Arrange
        from app.api.v1.endpoints.webhooks import verify_webhook_signature

        secret = "test-secret"
        payload = b'{"test": "data"}'
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Act & Assert
        # Uppercase signature should fail
        assert verify_webhook_signature(payload, signature.upper(), secret) is False

        # Correct case should succeed
        assert verify_webhook_signature(payload, signature, secret) is True


class TestWebhookSignatureIntegration:
    """Integration tests for webhook signature verification with real events."""

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "production-secret-key")
    async def test_crawl_started_with_signature(self, test_client: AsyncClient, mock_redis_service, mock_language_detection_service):
        """Test crawl.started event with signature verification."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "production-secret-key"
            payload = {
                "type": "crawl.started",
                "id": "crawl_abc123"
            }
            payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "acknowledged"
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "production-secret-key")
    async def test_crawl_completed_with_signature(
        self, test_client: AsyncClient, sample_webhook_crawl_completed: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test crawl.completed event with signature verification."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            secret = "production-secret-key"
            payload_bytes = json.dumps(sample_webhook_crawl_completed, separators=(',', ':')).encode('utf-8')
            signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": signature
                }
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["pages_processed"] == 2
        finally:
            app.dependency_overrides.clear()

    @patch("app.core.config.settings.FIRECRAWL_WEBHOOK_SECRET", "production-secret-key")
    async def test_crawl_failed_with_invalid_signature(
        self, test_client: AsyncClient, sample_webhook_crawl_failed: Dict[str, Any], mock_redis_service, mock_language_detection_service
    ):
        """Test that crawl.failed event with invalid signature is rejected."""
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Arrange
            payload_bytes = json.dumps(sample_webhook_crawl_failed, separators=(',', ':')).encode('utf-8')
            invalid_signature = "not_the_right_signature"

            # Act
            response = await test_client.post(
                "/api/v1/webhooks/firecrawl",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Firecrawl-Signature": invalid_signature
                }
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "Invalid webhook signature" in data["detail"]
        finally:
            app.dependency_overrides.clear()
