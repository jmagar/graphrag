"""
Tests for configuration validation.

Tests that Pydantic validators catch misconfigurations at startup.
"""

import pytest
from unittest.mock import patch
import os
from pydantic import ValidationError


class TestConfigValidation:
    """Test suite for configuration validation."""

    def test_redis_port_validation_rejects_invalid_ports(self):
        """
        Test that ports < 1 or > 65535 raise ValueError.
        
        RED: This test will FAIL initially (no port validation).
        """
        # Test port too low
        with patch.dict(os.environ, {
            'REDIS_PORT': '0',
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'  # Allow missing webhook secret
        }):
            with pytest.raises(ValidationError, match="Redis port"):
                from app.core.config import Settings
                Settings()
        
        # Test port too high
        with patch.dict(os.environ, {
            'REDIS_PORT': '65536',
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'
        }):
            with pytest.raises(ValidationError, match="Redis port"):
                from app.core.config import Settings
                Settings()

    def test_allowed_languages_validation_rejects_invalid_codes(self):
        """
        Test that invalid language codes raise ValueError with suggestions.
        
        RED: This test will FAIL initially (no language validation).
        """
        with patch.dict(os.environ, {
            'ALLOWED_LANGUAGES': 'en,xx,yy',  # xx and yy are invalid
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'
        }):
            with pytest.raises(ValidationError, match="language codes"):
                from app.core.config import Settings
                Settings()

    def test_language_filter_mode_validation(self):
        """
        Test that only 'strict' and 'lenient' modes are accepted.
        
        RED: This test will FAIL initially (no mode validation).
        """
        with patch.dict(os.environ, {
            'LANGUAGE_FILTER_MODE': 'invalid',
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'
        }):
            with pytest.raises(ValidationError, match="filter mode"):
                from app.core.config import Settings
                Settings()

    def test_webhook_url_validation(self):
        """
        Test that invalid URLs raise ValueError.
        
        RED: This test will FAIL initially (no URL validation).
        """
        with patch.dict(os.environ, {
            'WEBHOOK_BASE_URL': 'not-a-url',
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'
        }):
            with pytest.raises(ValidationError, match="webhook URL|URL"):
                from app.core.config import Settings
                Settings()

    def test_feature_flag_cross_validation(self):
        """
        Test that conflicting feature flags are detected.
        
        RED: This test will FAIL initially (no cross-validation).
        """
        # Language filtering enabled but no languages specified
        with patch.dict(os.environ, {
            'ENABLE_LANGUAGE_FILTERING': 'true',
            'ALLOWED_LANGUAGES': '',
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'
        }):
            with pytest.raises(ValidationError, match="ALLOWED_LANGUAGES"):
                from app.core.config import Settings
                Settings()

    def test_config_summary_masks_secrets(self):
        """
        Test that API keys and passwords are not shown in config summary.
        
        RED: This test will FAIL initially (no get_config_summary method).
        """
        with patch.dict(os.environ, {
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'super-secret-key-123',
            'FIRECRAWL_WEBHOOK_SECRET': 'super-secret-webhook',
            'REDIS_PASSWORD': 'redis-password-123',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'true'
        }):
            from app.core.config import Settings
            config = Settings()
            
            summary = config.get_config_summary()
            
            # Secrets should not appear in summary
            summary_str = str(summary)
            assert 'super-secret-key-123' not in summary_str
            assert 'super-secret-webhook' not in summary_str
            assert 'redis-password-123' not in summary_str
            
            # But should show that they are set
            assert summary['services']['firecrawl_key_set'] is True
            assert summary['services']['webhook_secret_set'] is True
            assert summary['redis']['password_set'] is True

    def test_production_mode_validations_stricter(self):
        """
        Test that production mode (DEBUG=false) has stricter validations.
        
        This is already tested in webhook security tests, just verify it works.
        """
        # This should fail because webhook secret is required in production
        with patch.dict(os.environ, {
            'FIRECRAWL_URL': 'http://localhost:4200',
            'FIRECRAWL_API_KEY': 'test-key',
            'FIRECRAWL_WEBHOOK_SECRET': '',
            'QDRANT_URL': 'http://localhost:4203',
            'TEI_URL': 'http://localhost:4207',
            'DEBUG': 'false'  # Production mode
        }):
            with pytest.raises(ValueError, match="FIRECRAWL_WEBHOOK_SECRET"):
                from app.core.config import Settings
                Settings()
