"""
Tests for webhook security enforcement.

Tests webhook signature verification is mandatory in production mode.
"""

import pytest
import hmac
import hashlib
import json
import os
from unittest.mock import patch, AsyncMock
from app.core.config import settings


def generate_valid_signature(payload: bytes, secret: str) -> str:
    """Helper to generate valid HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class TestWebhookSecurity:
    """Test suite for webhook security enforcement."""

    @pytest.mark.anyio
    async def test_webhook_rejects_missing_secret_in_production(self, test_client):
        """
        Test that webhook returns 500 when secret not configured in production mode.
        
        RED: This test should FAIL initially (no enforcement yet).
        """
        with patch.object(settings, 'FIRECRAWL_WEBHOOK_SECRET', ''):
            with patch.object(settings, 'DEBUG', False):
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

    @pytest.mark.anyio
    async def test_webhook_accepts_missing_secret_in_debug(self, test_client):
        """
        Test that webhook accepts requests without secret in DEBUG mode.
        
        This ensures backward compatibility for development.
        """
        with patch.object(settings, 'FIRECRAWL_WEBHOOK_SECRET', ''):
            with patch.object(settings, 'DEBUG', True):
                with patch('app.api.v1.endpoints.webhooks.redis_service.mark_page_processed', new_callable=AsyncMock):
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

    @pytest.mark.anyio
    async def test_webhook_rejects_invalid_signature(self, test_client):
        """
        Test that webhook returns 401 with invalid signature.
        """
        secret = "test-webhook-secret"
        
        with patch.object(settings, 'FIRECRAWL_WEBHOOK_SECRET', secret):
            with patch.object(settings, 'DEBUG', False):
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

    @pytest.mark.anyio
    async def test_webhook_accepts_valid_signature(self, test_client):
        """
        Test that webhook processes request with valid HMAC signature.
        """
        secret = "test-webhook-secret"
        
        with patch.object(settings, 'FIRECRAWL_WEBHOOK_SECRET', secret):
            with patch.object(settings, 'DEBUG', False):
                with patch('app.api.v1.endpoints.webhooks.redis_service.mark_page_processed', new_callable=AsyncMock):
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

    @pytest.mark.anyio
    async def test_webhook_logs_security_events(self, test_client, caplog):
        """
        Test that security events are logged properly.
        """
        secret = "test-webhook-secret"
        
        with patch.object(settings, 'FIRECRAWL_WEBHOOK_SECRET', secret):
            with patch.object(settings, 'DEBUG', False):
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
