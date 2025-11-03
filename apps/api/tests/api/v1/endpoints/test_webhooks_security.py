"""
Tests for webhook security enforcement.

Tests webhook signature verification is mandatory in production mode.
"""

import pytest
import hmac
import hashlib
import json
from unittest.mock import patch, AsyncMock
from app.main import app
from app.dependencies import get_redis_service, get_language_detection_service


def generate_valid_signature(payload: bytes, secret: str) -> str:
    """Helper to generate valid HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class TestWebhookSecurity:
    """Test suite for webhook security enforcement."""

    @pytest.mark.anyio
    async def test_webhook_rejects_missing_secret_in_production(
        self, test_client, mock_redis_service, mock_language_detection_service
    ):
        """
        Test that webhook returns 500 when secret not configured in production mode.
        
        RED: This test should FAIL initially (no enforcement yet).
        """
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Patch settings where it's imported in the webhook module
            with patch('app.api.v1.endpoints.webhooks.settings.FIRECRAWL_WEBHOOK_SECRET', ''):
                with patch('app.api.v1.endpoints.webhooks.settings.DEBUG', False):
                    payload = {
                        "type": "crawl.started",
                        "id": "test-crawl-123"
                    }
                    
                    response = await test_client.post(
                        "/api/v1/webhooks/firecrawl",
                        json=payload
                    )
                    
                    assert response.status_code == 500
                    assert "security not properly configured" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_webhook_accepts_missing_secret_in_debug(
        self, test_client, mock_redis_service, mock_language_detection_service
    ):
        """
        Test that webhook accepts requests without secret in DEBUG mode.
        
        This ensures backward compatibility for development.
        """
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            # Patch settings where it's imported in the webhook module
            with patch('app.api.v1.endpoints.webhooks.settings.FIRECRAWL_WEBHOOK_SECRET', ''):
                with patch('app.api.v1.endpoints.webhooks.settings.DEBUG', True):
                    with patch('app.api.v1.endpoints.webhooks.process_crawled_page', new_callable=AsyncMock):
                        payload = {
                            "type": "crawl.started",
                            "id": "test-crawl-123"
                        }
                        
                        response = await test_client.post(
                            "/api/v1/webhooks/firecrawl",
                            json=payload
                        )
                        
                        assert response.status_code == 200
                        assert response.json()["status"] == "acknowledged"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_webhook_rejects_invalid_signature(
        self, test_client, mock_redis_service, mock_language_detection_service
    ):
        """
        Test that webhook returns 401 with invalid signature.
        """
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            secret = "test-webhook-secret"
            
            # Patch settings where it's imported in the webhook module
            with patch('app.api.v1.endpoints.webhooks.settings.FIRECRAWL_WEBHOOK_SECRET', secret):
                with patch('app.api.v1.endpoints.webhooks.settings.DEBUG', False):
                    payload = {
                        "type": "crawl.started",
                        "id": "test-crawl-123"
                    }
                    payload_bytes = json.dumps(payload).encode()
                    
                    # Send request with INVALID signature
                    response = await test_client.post(
                        "/api/v1/webhooks/firecrawl",
                        content=payload_bytes,
                        headers={
                            "X-Firecrawl-Signature": "invalid-signature-12345",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    assert response.status_code == 401
                    assert "invalid webhook signature" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_webhook_accepts_valid_signature(
        self, test_client, mock_redis_service, mock_language_detection_service
    ):
        """
        Test that webhook processes request with valid HMAC signature.
        """
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            secret = "test-webhook-secret"
            
            # Patch settings where it's imported in the webhook module
            with patch('app.api.v1.endpoints.webhooks.settings.FIRECRAWL_WEBHOOK_SECRET', secret):
                with patch('app.api.v1.endpoints.webhooks.settings.DEBUG', False):
                    with patch('app.api.v1.endpoints.webhooks.process_crawled_page', new_callable=AsyncMock):
                        payload = {
                            "type": "crawl.started",
                            "id": "test-crawl-123"
                        }
                        payload_bytes = json.dumps(payload).encode()
                        
                        # Generate valid signature
                        valid_signature = generate_valid_signature(payload_bytes, secret)
                        
                        # Send request with VALID signature
                        response = await test_client.post(
                            "/api/v1/webhooks/firecrawl",
                            content=payload_bytes,
                            headers={
                                "X-Firecrawl-Signature": valid_signature,
                                "Content-Type": "application/json"
                            }
                        )
                        
                        assert response.status_code == 200
                        assert response.json()["status"] == "acknowledged"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_webhook_logs_security_events(
        self, test_client, mock_redis_service, mock_language_detection_service, caplog
    ):
        """
        Test that security events are logged properly.
        """
        app.dependency_overrides[get_redis_service] = lambda: mock_redis_service
        app.dependency_overrides[get_language_detection_service] = lambda: mock_language_detection_service
        
        try:
            secret = "test-webhook-secret"
            
            # Patch settings where it's imported in the webhook module
            with patch('app.api.v1.endpoints.webhooks.settings.FIRECRAWL_WEBHOOK_SECRET', secret):
                with patch('app.api.v1.endpoints.webhooks.settings.DEBUG', False):
                    payload = {
                        "type": "crawl.started",
                        "id": "test-crawl-123"
                    }
                    payload_bytes = json.dumps(payload).encode()
                    
                    # Test with invalid signature
                    response = await test_client.post(
                        "/api/v1/webhooks/firecrawl",
                        content=payload_bytes,
                        headers={
                            "X-Firecrawl-Signature": "invalid",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    assert response.status_code == 401
                    # Check that security warning was logged
                    assert any("Invalid webhook signature" in record.message for record in caplog.records)
        finally:
            app.dependency_overrides.clear()

    def test_production_startup_fails_without_secret(self):
        """
        Test that application startup validation fails when secret missing in production.
        
        This tests the Settings.validate_webhook_config() method.
        """
        with patch.dict('os.environ', {
            'FIRECRAWL_WEBHOOK_SECRET': '',
            'DEBUG': 'false',
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207'
        }):
            # Importing Settings should raise ValueError due to validation
            with pytest.raises(ValueError, match="FIRECRAWL_WEBHOOK_SECRET is required in production"):
                from app.core.config import Settings
                Settings()
