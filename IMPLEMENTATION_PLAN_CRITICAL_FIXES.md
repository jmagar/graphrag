# Implementation Plan: Critical & High-Priority Fixes

**Created:** 2025-11-01  
**Status:** Ready for Implementation  
**Estimated Total Time:** 3-4 hours  

This document provides a detailed implementation plan for all critical and high-priority issues identified in the code review.

---

## Table of Contents

1. [Critical Priority Issues](#critical-priority-issues)
   - [Issue #6: Webhook Signature Verification Enforcement](#issue-6-webhook-signature-verification-enforcement)
   - [Issue #1: FirecrawlService Resource Cleanup](#issue-1-firecrawlservice-resource-cleanup)
2. [High Priority Issues](#high-priority-issues)
   - [Issue #4: Language Detection Caching](#issue-4-language-detection-caching)
   - [Issue #9: Configuration Validation](#issue-9-configuration-validation)
   - [Issue #10: Rate Limiting Strategy Documentation](#issue-10-rate-limiting-strategy-documentation)
3. [Implementation Order](#implementation-order)
4. [Testing Strategy](#testing-strategy)

---

## Critical Priority Issues

### Issue #6: Webhook Signature Verification Enforcement

**Priority:** P0 (Critical)  
**Estimated Time:** 15 minutes  
**Impact:** Security vulnerability - prevents unauthorized webhook injection  

#### Overview
Currently, webhook signature verification is optional. If `FIRECRAWL_WEBHOOK_SECRET` is not set, any request is accepted. This allows attackers to inject fake crawl data into the system. We need to make signature verification mandatory in production environments.

#### Files to Change

1. **`apps/api/app/api/v1/endpoints/webhooks.py`**
   - Enforce signature verification in production
   - Add clear error messages for missing secret

2. **`apps/api/app/core/config.py`**
   - Update environment variable documentation
   - Add validation for required secrets in production

3. **`apps/api/.env.example`**
   - Update documentation with security warnings

#### Functions to Implement

##### `apps/api/app/api/v1/endpoints/webhooks.py`

**Function:** `_validate_webhook_security()`
- New helper function that checks if webhook security is properly configured
- Raises HTTPException if secret is missing in non-DEBUG mode
- Returns early if DEBUG mode allows insecure webhooks

**Modified:** `firecrawl_webhook()`
- Call `_validate_webhook_security()` at the start of the endpoint
- Add structured logging for security events
- Maintain backward compatibility for DEBUG mode

##### `apps/api/app/core/config.py`

**Property:** `is_production`
- Returns `True` if not in DEBUG mode
- Used to determine if strict security checks should apply

**Method:** `validate_webhook_config()`
- Validator method that checks webhook secret is set in production
- Logs warning if running in insecure mode
- Called during Settings initialization

#### Tests to Implement

##### `apps/api/tests/api/v1/endpoints/test_webhooks_security.py`

**Test:** `test_webhook_rejects_missing_secret_in_production`
- Webhook returns 500 when secret not configured in production mode

**Test:** `test_webhook_accepts_missing_secret_in_debug`
- Webhook accepts requests without secret in DEBUG mode

**Test:** `test_webhook_rejects_invalid_signature`
- Webhook returns 401 with invalid signature header

**Test:** `test_webhook_accepts_valid_signature`
- Webhook processes request with valid HMAC signature

**Test:** `test_webhook_logs_security_events`
- Security events logged for missing secrets and invalid signatures

**Test:** `test_production_startup_fails_without_secret`
- Application startup validation fails when secret missing in production

#### Implementation Details

```python
# apps/api/app/api/v1/endpoints/webhooks.py

def _validate_webhook_security() -> None:
    """
    Validate webhook security configuration.
    
    Raises:
        HTTPException: If webhook secret is not configured in production
    """
    if not settings.FIRECRAWL_WEBHOOK_SECRET:
        if settings.is_production:
            logger.critical("❌ SECURITY: Webhook secret not configured in production")
            raise HTTPException(
                status_code=500,
                detail="Webhook security not properly configured"
            )
        else:
            logger.warning("⚠️ INSECURE: Running webhooks without signature verification in DEBUG mode")


@router.post("/firecrawl")
async def firecrawl_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Firecrawl webhook endpoint with mandatory signature verification in production.
    """
    # Validate security configuration
    _validate_webhook_security()
    
    # Verify signature if secret is configured
    if settings.FIRECRAWL_WEBHOOK_SECRET:
        body = await request.body()
        signature = request.headers.get("X-Firecrawl-Signature", "")
        
        if not verify_webhook_signature(body, signature, settings.FIRECRAWL_WEBHOOK_SECRET):
            logger.warning(
                "🚨 Invalid webhook signature",
                extra={
                    "ip": request.client.host,
                    "signature": signature[:20] + "...",
                }
            )
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        logger.debug("✅ Webhook signature verified")
        payload_dict = json.loads(body.decode("utf-8"))
    else:
        # DEBUG mode - skip verification but log warning
        logger.debug("⚠️ Webhook processed without signature verification (DEBUG mode)")
        payload_dict = await request.json()
    
    # ... rest of webhook processing
```

```python
# apps/api/app/core/config.py

class Settings(BaseSettings):
    # ... existing fields ...
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG
    
    def validate_webhook_config(self) -> None:
        """Validate webhook configuration for production."""
        if self.is_production and not self.FIRECRAWL_WEBHOOK_SECRET:
            logger.error(
                "❌ CONFIGURATION ERROR: FIRECRAWL_WEBHOOK_SECRET must be set in production"
            )
            raise ValueError(
                "FIRECRAWL_WEBHOOK_SECRET is required in production mode. "
                "Set DEBUG=true to allow insecure webhooks in development."
            )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_webhook_config()
```

---

### Issue #1: FirecrawlService Resource Cleanup

**Priority:** P0 (Critical)  
**Estimated Time:** 30 minutes  
**Impact:** Connection leaks, resource exhaustion under high load  

#### Overview
The `FirecrawlService` creates a persistent HTTP client with connection pooling, but the `close()` method is never called. This can lead to connection leaks when the application shuts down or during hot reloads. We need to integrate proper cleanup into the FastAPI lifespan.

#### Files to Change

1. **`apps/api/app/main.py`**
   - Add service cleanup to lifespan context manager
   - Initialize service singleton

2. **`apps/api/app/services/firecrawl.py`**
   - Improve close() method with error handling
   - Add context manager support

3. **`apps/api/app/api/v1/endpoints/crawl.py`**
   - Use dependency injection for FirecrawlService
   - Ensure service instance is reused

#### Functions to Implement

##### `apps/api/app/main.py`

**Modified:** `lifespan(app: FastAPI)`
- Initialize FirecrawlService singleton during startup
- Call cleanup methods during shutdown
- Handle cleanup errors gracefully with logging

**Function:** `get_firecrawl_service()`
- Dependency injection function for FastAPI endpoints
- Returns the singleton FirecrawlService instance
- Ensures service is initialized before use

##### `apps/api/app/services/firecrawl.py`

**Modified:** `close()`
- Add try-except error handling around client closure
- Log successful cleanup
- Set _client to None even if closure fails

**Methods:** `__aenter__()` and `__aexit__()`
- Add async context manager support
- Allow `async with FirecrawlService() as service:` usage
- Automatically handle cleanup

**Property:** `is_closed`
- Returns True if client is None or closed
- Used for health checks and debugging

#### Tests to Implement

##### `apps/api/tests/services/test_firecrawl_lifecycle.py`

**Test:** `test_firecrawl_service_creates_client_on_first_use`
- Client is None before first API call
- Client created lazily on first request

**Test:** `test_firecrawl_service_reuses_client`
- Multiple API calls use same client instance
- Connection pooling working correctly

**Test:** `test_firecrawl_service_close_releases_connections`
- Client is closed and set to None after close()
- Subsequent calls create new client

**Test:** `test_firecrawl_service_close_handles_errors`
- close() doesn't raise exception if client already closed
- Errors logged but don't propagate

**Test:** `test_firecrawl_service_context_manager`
- Context manager automatically closes client on exit
- Client available within context block

**Test:** `test_lifespan_cleanup_calls_service_close`
- Application shutdown triggers service cleanup
- All services properly closed

##### `apps/api/tests/api/v1/endpoints/test_crawl_lifecycle.py`

**Test:** `test_crawl_endpoint_uses_singleton_service`
- Multiple requests use same FirecrawlService instance
- No service instance proliferation

#### Implementation Details

```python
# apps/api/app/main.py

from contextlib import asynccontextmanager
from app.services.firecrawl import FirecrawlService

# Global service instances
_firecrawl_service: Optional[FirecrawlService] = None


def get_firecrawl_service() -> FirecrawlService:
    """
    Get the singleton FirecrawlService instance.
    
    Returns:
        FirecrawlService: Singleton service instance
        
    Raises:
        RuntimeError: If service not initialized (app not started)
    """
    global _firecrawl_service
    if _firecrawl_service is None:
        raise RuntimeError("FirecrawlService not initialized. Application may not be started.")
    return _firecrawl_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with proper resource cleanup.
    """
    global _firecrawl_service
    
    # Startup: Initialize services
    logger.info("🚀 Starting GraphRAG API...")
    
    # Initialize FirecrawlService singleton
    _firecrawl_service = FirecrawlService()
    logger.info("✅ FirecrawlService initialized")
    
    # ... existing startup code ...
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("🛑 Shutting down GraphRAG API...")
    
    # Close FirecrawlService
    if _firecrawl_service:
        try:
            await _firecrawl_service.close()
            logger.info("✅ FirecrawlService closed")
        except Exception as e:
            logger.error(f"❌ Error closing FirecrawlService: {e}")
    
    logger.info("👋 GraphRAG API shutdown complete")


app = FastAPI(lifespan=lifespan, ...)
```

```python
# apps/api/app/services/firecrawl.py

class FirecrawlService:
    """
    Service for interacting with Firecrawl v2 API.
    
    Supports async context manager for automatic cleanup:
        async with FirecrawlService() as service:
            await service.start_crawl(...)
    """
    
    async def close(self) -> None:
        """
        Close the HTTP client and release connections.
        
        Safe to call multiple times. Errors are logged but not raised.
        """
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
                logger.info("🔌 HTTP client connections closed")
            except Exception as e:
                logger.error(f"Error closing HTTP client: {e}")
            finally:
                self._client = None
        else:
            logger.debug("HTTP client already closed or not initialized")
    
    @property
    def is_closed(self) -> bool:
        """Check if the HTTP client is closed."""
        return self._client is None or self._client.is_closed
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with automatic cleanup."""
        await self.close()
        return False  # Don't suppress exceptions
```

```python
# apps/api/app/api/v1/endpoints/crawl.py

from fastapi import APIRouter, Depends
from app.main import get_firecrawl_service

router = APIRouter()


@router.post("/")
async def start_crawl(
    request: CrawlRequest,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service)
):
    """
    Start a new crawl job using the singleton FirecrawlService.
    """
    crawl_options = {
        "url": request.url,
        # ... other options
    }
    
    result = await firecrawl_service.start_crawl(crawl_options)
    return result
```

---

## High Priority Issues

### Issue #4: Language Detection Caching

**Priority:** P1 (High)  
**Estimated Time:** 45 minutes  
**Impact:** 10-50ms performance improvement per page on large crawls  

#### Overview
Language detection runs on EVERY page during crawl processing, using `langdetect` which takes 10-50ms per call. For large crawls (1000+ pages), this adds significant overhead. We can cache detection results based on content hash to avoid redundant processing.

#### Files to Change

1. **`apps/api/app/services/language_detection.py`**
   - Add LRU cache decorator to detection logic
   - Implement content-based cache key generation
   - Add cache statistics tracking

2. **`apps/api/app/core/config.py`**
   - Add cache configuration settings
   - Configure cache size limits

#### Functions to Implement

##### `apps/api/app/services/language_detection.py`

**Function:** `_generate_cache_key(text: str) -> str`
- Creates MD5 hash of text sample (first 2000 chars)
- Returns hex digest as cache key
- Used for deduplication of identical content

**Function:** `_detect_language_impl(text_sample: str) -> str`
- Internal implementation of language detection
- Decorated with @lru_cache for memoization
- Called by public detect_language method

**Modified:** `detect_language(text: str) -> str`
- Generate cache key from text
- Call cached implementation
- Add cache hit/miss logging

**Method:** `get_cache_stats() -> Dict[str, int]`
- Returns cache hit/miss statistics
- Used for monitoring and optimization
- Includes cache size and hit rate

**Method:** `clear_cache() -> None`
- Clears the language detection cache
- Used for testing and manual cache invalidation
- Logs cache clear event

##### `apps/api/app/core/config.py`

**Settings:**
- `LANGUAGE_DETECTION_CACHE_SIZE: int = 1000` - Maximum cached entries
- `LANGUAGE_DETECTION_SAMPLE_SIZE: int = 2000` - Chars to sample for detection

#### Tests to Implement

##### `apps/api/tests/services/test_language_detection_cache.py`

**Test:** `test_language_detection_caches_results`
- Same text detected only once, subsequent calls cached
- Cache key generation working correctly

**Test:** `test_cache_handles_different_content`
- Different content generates different cache keys
- Cache doesn't incorrectly reuse results

**Test:** `test_cache_respects_size_limit`
- Cache evicts oldest entries when limit reached
- LRU eviction working correctly

**Test:** `test_cache_stats_tracking`
- Cache hits and misses tracked correctly
- Statistics accurate after multiple detections

**Test:** `test_clear_cache_resets_state`
- clear_cache() removes all entries
- Subsequent calls re-detect language

**Test:** `test_cache_performance_improvement`
- Cached calls significantly faster than uncached
- Performance gain measurable

**Test:** `test_cache_key_stability`
- Same text produces same cache key
- Cache keys deterministic

#### Implementation Details

```python
# apps/api/app/services/language_detection.py

import hashlib
import logging
from functools import lru_cache
from typing import Dict
from langdetect import detect, LangDetectException
from app.core.config import settings

logger = logging.getLogger(__name__)


class LanguageDetectionService:
    """
    Service for detecting language of text content with caching.
    
    Caches detection results based on content hash to avoid redundant
    processing of identical or similar content.
    """
    
    def __init__(self, min_text_length: int = 50):
        self.min_text_length = min_text_length
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _generate_cache_key(self, text: str) -> str:
        """
        Generate cache key from text content.
        
        Args:
            text: Text to hash
            
        Returns:
            MD5 hex digest of text sample
        """
        sample = text[:settings.LANGUAGE_DETECTION_SAMPLE_SIZE]
        return hashlib.md5(sample.encode('utf-8', errors='ignore')).hexdigest()
    
    @lru_cache(maxsize=1000)
    def _detect_language_impl(self, cache_key: str, text_sample: str) -> str:
        """
        Internal cached language detection implementation.
        
        Args:
            cache_key: Hash of content (for cache keying)
            text_sample: Text sample to detect
            
        Returns:
            Language code or 'unknown'
        """
        try:
            lang = detect(text_sample)
            logger.debug(f"Detected language: {lang} (cache_key: {cache_key[:8]}...)")
            return lang
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return "unknown"
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text with caching.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Language code (e.g., 'en', 'es', 'fr') or 'unknown'
        """
        if not text or len(text) < self.min_text_length:
            logger.debug("Text too short for language detection")
            return "unknown"
        
        # Generate cache key
        sample = text[:settings.LANGUAGE_DETECTION_SAMPLE_SIZE]
        cache_key = self._generate_cache_key(text)
        
        # Check if this is a cache hit (by inspecting LRU cache)
        cache_info_before = self._detect_language_impl.cache_info()
        
        # Call cached implementation
        result = self._detect_language_impl(cache_key, sample)
        
        # Track cache statistics
        cache_info_after = self._detect_language_impl.cache_info()
        if cache_info_after.hits > cache_info_before.hits:
            self._cache_hits += 1
            logger.debug(f"Cache hit for language detection: {result}")
        else:
            self._cache_misses += 1
        
        return result
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hits, misses, size, and hit_rate
        """
        cache_info = self._detect_language_impl.cache_info()
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "cache_size": cache_info.currsize,
            "cache_maxsize": cache_info.maxsize,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def clear_cache(self) -> None:
        """Clear the language detection cache."""
        self._detect_language_impl.cache_clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Language detection cache cleared")
    
    # Keep existing methods (is_english, is_allowed_language, etc.)
```

---

### Issue #9: Configuration Validation

**Priority:** P1 (High)  
**Estimated Time:** 1 hour  
**Impact:** Prevents misconfiguration, improves developer experience  

#### Overview
The configuration file has 30+ environment variables. Invalid values (wrong ports, unsupported languages, invalid URLs) can cause runtime errors. We need Pydantic validators to catch these issues at startup.

#### Files to Change

1. **`apps/api/app/core/config.py`**
   - Add Pydantic validators for all critical settings
   - Validate port ranges, language codes, URLs
   - Add cross-field validation logic

2. **`apps/api/app/main.py`**
   - Add configuration validation logging during startup
   - Display validated config summary

#### Functions to Implement

##### `apps/api/app/core/config.py`

**Validator:** `validate_redis_port(cls, v) -> int`
- Ensures Redis port is in valid range (1-65535)
- Raises ValueError with helpful message if invalid

**Validator:** `validate_allowed_languages(cls, v) -> str`
- Validates language codes against supported list
- Checks format (lowercase, 2-letter ISO codes)
- Provides suggestions if invalid code provided

**Validator:** `validate_language_filter_mode(cls, v) -> str`
- Ensures mode is either "strict" or "lenient"
- Raises error for unsupported modes

**Validator:** `validate_webhook_base_url(cls, v) -> str`
- Ensures URL is valid HTTP/HTTPS
- Warns if using localhost in production
- Validates URL format

**Validator:** `validate_feature_flags(cls, values) -> dict`
- Cross-field validation for feature flag combinations
- Warns about conflicting flag configurations
- Ensures required dependencies are met

**Method:** `get_config_summary() -> Dict[str, Any]`
- Returns sanitized configuration summary
- Masks sensitive values (API keys, passwords)
- Used for startup logging and debugging

##### `apps/api/app/main.py`

**Function:** `log_startup_configuration()`
- Logs validated configuration during startup
- Shows enabled features and critical settings
- Helps with troubleshooting deployment issues

#### Tests to Implement

##### `apps/api/tests/core/test_config_validation.py`

**Test:** `test_redis_port_validation_rejects_invalid_ports`
- Ports < 1 or > 65535 raise ValueError
- Valid ports (1-65535) accepted

**Test:** `test_allowed_languages_validation_rejects_invalid_codes`
- Invalid language codes raise ValueError with suggestions
- Valid ISO 639-1 codes accepted

**Test:** `test_language_filter_mode_validation`
- Only "strict" and "lenient" modes accepted
- Case-insensitive validation working

**Test:** `test_webhook_url_validation`
- Invalid URLs raise ValueError
- Valid HTTP/HTTPS URLs accepted

**Test:** `test_feature_flag_cross_validation`
- Conflicting feature flags detected and warned
- Valid combinations accepted

**Test:** `test_config_summary_masks_secrets`
- API keys and passwords not shown in summary
- Other values displayed correctly

**Test:** `test_production_mode_validations_stricter`
- Production mode enforces additional validations
- Debug mode more lenient

#### Implementation Details

```python
# apps/api/app/core/config.py

from pydantic import field_validator, model_validator
from typing import Dict, Any
import re


# Supported language codes (ISO 639-1)
SUPPORTED_LANGUAGES = [
    'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'zh', 'ko',
    'ar', 'hi', 'nl', 'pl', 'tr', 'vi', 'th', 'sv', 'no', 'da'
]


class Settings(BaseSettings):
    # ... existing fields ...
    
    @field_validator('REDIS_PORT')
    @classmethod
    def validate_redis_port(cls, v: int) -> int:
        """Validate Redis port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(
                f"Invalid Redis port: {v}. Must be between 1 and 65535."
            )
        return v
    
    @field_validator('ALLOWED_LANGUAGES')
    @classmethod
    def validate_allowed_languages(cls, v: str) -> str:
        """Validate language codes are supported."""
        if not v:
            return v
        
        codes = [lang.strip().lower() for lang in v.split(',')]
        invalid_codes = [code for code in codes if code not in SUPPORTED_LANGUAGES]
        
        if invalid_codes:
            raise ValueError(
                f"Unsupported language codes: {invalid_codes}. "
                f"Supported codes: {SUPPORTED_LANGUAGES}"
            )
        
        # Return normalized (lowercase, no spaces)
        return ','.join(codes)
    
    @field_validator('LANGUAGE_FILTER_MODE')
    @classmethod
    def validate_language_filter_mode(cls, v: str) -> str:
        """Validate language filter mode."""
        v = v.lower()
        if v not in ('strict', 'lenient'):
            raise ValueError(
                f"Invalid language filter mode: {v}. Must be 'strict' or 'lenient'."
            )
        return v
    
    @field_validator('WEBHOOK_BASE_URL')
    @classmethod
    def validate_webhook_base_url(cls, v: str) -> str:
        """Validate webhook base URL format."""
        if not re.match(r'^https?://', v):
            raise ValueError(
                f"Invalid webhook URL: {v}. Must start with http:// or https://"
            )
        
        # Warn about localhost in production
        if 'localhost' in v or '127.0.0.1' in v:
            logger.warning(
                "⚠️ Webhook URL uses localhost. This won't work if Firecrawl "
                "is on a different host. Consider using a public URL or container name."
            )
        
        return v.rstrip('/')  # Remove trailing slash
    
    @model_validator(mode='after')
    def validate_feature_flags(self) -> 'Settings':
        """Cross-field validation for feature flags."""
        # If language filtering is enabled, ensure languages are configured
        if self.ENABLE_LANGUAGE_FILTERING and not self.ALLOWED_LANGUAGES:
            raise ValueError(
                "ENABLE_LANGUAGE_FILTERING is true but ALLOWED_LANGUAGES is empty. "
                "Specify at least one language code or disable the feature."
            )
        
        # Warn about feature flag combinations
        if self.ENABLE_STREAMING_PROCESSING and self.ENABLE_LANGUAGE_FILTERING:
            logger.info(
                "ℹ️ Both streaming and language filtering enabled. "
                "Pages will be filtered before processing."
            )
        
        return self
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get sanitized configuration summary for logging.
        
        Returns:
            Dictionary with config values, sensitive data masked
        """
        return {
            "debug": self.DEBUG,
            "redis": {
                "host": self.REDIS_HOST,
                "port": self.REDIS_PORT,
                "db": self.REDIS_DB,
                "password_set": bool(self.REDIS_PASSWORD)
            },
            "features": {
                "streaming_processing": self.ENABLE_STREAMING_PROCESSING,
                "language_filtering": self.ENABLE_LANGUAGE_FILTERING
            },
            "language": {
                "allowed": self.allowed_languages_list if self.ENABLE_LANGUAGE_FILTERING else None,
                "mode": self.LANGUAGE_FILTER_MODE if self.ENABLE_LANGUAGE_FILTERING else None
            },
            "services": {
                "firecrawl_url": self.FIRECRAWL_URL,
                "firecrawl_key_set": bool(self.FIRECRAWL_API_KEY),
                "webhook_secret_set": bool(self.FIRECRAWL_WEBHOOK_SECRET),
                "qdrant_url": self.QDRANT_URL,
                "tei_url": self.TEI_URL,
                "ollama_url": self.OLLAMA_URL
            }
        }
```

```python
# apps/api/app/main.py

def log_startup_configuration():
    """Log validated configuration during startup."""
    config_summary = settings.get_config_summary()
    
    logger.info("📋 Configuration Summary:")
    logger.info(f"  Mode: {'DEBUG' if config_summary['debug'] else 'PRODUCTION'}")
    logger.info(f"  Redis: {config_summary['redis']['host']}:{config_summary['redis']['port']}")
    logger.info(f"  Features: {config_summary['features']}")
    
    if config_summary['features']['language_filtering']:
        logger.info(
            f"  Languages: {config_summary['language']['allowed']} "
            f"({config_summary['language']['mode']} mode)"
        )
    
    logger.info(f"  Services configured: {len([k for k, v in config_summary['services'].items() if v])}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with configuration logging."""
    logger.info("🚀 Starting GraphRAG API...")
    
    # Log validated configuration
    log_startup_configuration()
    
    # ... rest of startup
```

---

### Issue #10: Rate Limiting Strategy Documentation

**Priority:** P1 (High)  
**Estimated Time:** 30 minutes  
**Impact:** Improves developer understanding, prevents misconfiguration  

#### Overview
The system has multi-layer rate limiting (client-side and server-side) with different limits. The current implementation has frontend limiting at 3 saves/10s and backend at 5 saves/10s. We need to document the rationale and ensure limits are coordinated.

#### Files to Change

1. **`apps/web/hooks/useConversationSave.ts`**
   - Add comprehensive documentation comments
   - Explain client-side limits rationale

2. **`apps/web/lib/apiMiddleware.ts`**
   - Document server-side limits
   - Explain coordination strategy

3. **`apps/web/lib/rateLimit.ts`**
   - Add JSDoc documentation for all classes
   - Document usage patterns

4. **`docs/architecture/RATE_LIMITING.md`** (new file)
   - Comprehensive rate limiting architecture doc
   - Configuration guide
   - Troubleshooting section

#### Documentation to Create

##### `docs/architecture/RATE_LIMITING.md`

**Sections:**
1. **Overview** - Why multi-layer rate limiting
2. **Architecture** - Client vs Server limiting
3. **Configuration** - How to adjust limits
4. **Monitoring** - How to track rate limit events
5. **Troubleshooting** - Common issues and solutions

##### Updated JSDoc Comments

**In `useConversationSave.ts`:**
- Document why client limit is MORE restrictive
- Explain deduplication strategy
- Provide usage examples

**In `apiMiddleware.ts`:**
- Document server-side limits as fallback
- Explain header-based tracking
- Document error responses

**In `rateLimit.ts`:**
- Document each class (RateLimiter, ClientRateLimiter, CircuitBreaker)
- Explain algorithms (sliding window, circuit breaker states)
- Provide configuration examples

#### Constants to Add

##### `apps/web/lib/rateLimit.ts`

```typescript
/**
 * Rate limiting constants with rationale.
 * 
 * CLIENT_SIDE limits are MORE restrictive than server limits to provide
 * immediate feedback and reduce unnecessary network calls.
 * 
 * SERVER_SIDE limits are the final enforcement layer and protect against
 * direct API access bypassing the frontend.
 */
export const RATE_LIMIT_CONFIG = {
  // Client-side limits (proactive)
  CLIENT_CONVERSATION_SAVE: {
    maxRequests: 3,
    windowMs: 10000, // 10 seconds
    rationale: "Prevents rapid-fire saves during UI interactions"
  },
  
  // Server-side limits (enforcement)
  SERVER_CONVERSATION_CREATE: {
    maxRequests: 10,
    windowMs: 60000, // 1 minute
    rationale: "Protects against conversation spam"
  },
  SERVER_MESSAGE_SAVE: {
    maxRequests: 5,
    windowMs: 10000, // 10 seconds
    rationale: "Protects against message spam while allowing legitimate bursts"
  }
} as const;
```

#### Tests to Implement

##### `apps/web/__tests__/lib/rateLimit.test.ts` (additions)

**Test:** `test_client_limits_more_restrictive_than_server`
- Verify client limits trigger before server limits
- Ensures proper layering strategy

**Test:** `test_rate_limit_constants_documented`
- All rate limit configs have rationale field
- Documentation present for all limits

#### Implementation Details

See the new documentation file created below for full implementation details.

---

## Implementation Order

Execute fixes in this order to minimize risk and maximize value:

### Phase 1: Critical Security (Day 1 - Morning)
1. ✅ **Issue #6** - Webhook signature enforcement (15 min)
2. ✅ **Issue #1** - FirecrawlService cleanup (30 min)

**Gate:** Run security tests, verify no connection leaks

### Phase 2: Performance & Validation (Day 1 - Afternoon)
3. ✅ **Issue #4** - Language detection caching (45 min)
4. ✅ **Issue #9** - Configuration validation (1 hour)

**Gate:** Run performance benchmarks, verify config validation

### Phase 3: Documentation (Day 2)
5. ✅ **Issue #10** - Rate limiting documentation (30 min)

**Gate:** Documentation review

---

## Testing Strategy

### Unit Tests
- Each issue has dedicated test file
- Minimum 80% code coverage for new code
- Test both happy path and error cases

### Integration Tests
- Test service lifecycle (startup → operation → shutdown)
- Test webhook security with real signature generation
- Test rate limiting under load

### Manual Testing Checklist

#### Issue #6 - Webhook Security
- [ ] Start app without FIRECRAWL_WEBHOOK_SECRET in production
- [ ] Verify startup fails with clear error message
- [ ] Start app with DEBUG=true, no secret
- [ ] Verify warning logged but app starts
- [ ] Send webhook with invalid signature
- [ ] Verify 401 response
- [ ] Send webhook with valid signature
- [ ] Verify processing succeeds

#### Issue #1 - Resource Cleanup
- [ ] Start application
- [ ] Trigger crawl endpoint
- [ ] Verify HTTP client created
- [ ] Stop application
- [ ] Check logs for cleanup message
- [ ] Verify no connection leak warnings

#### Issue #4 - Language Caching
- [ ] Enable language filtering
- [ ] Process 100 pages with same content
- [ ] Check cache statistics
- [ ] Verify high hit rate (>90%)
- [ ] Measure performance improvement

#### Issue #9 - Config Validation
- [ ] Set invalid Redis port (0)
- [ ] Verify startup fails with helpful error
- [ ] Set invalid language code
- [ ] Verify error message suggests valid codes
- [ ] Set ENABLE_LANGUAGE_FILTERING=true, ALLOWED_LANGUAGES=""
- [ ] Verify cross-field validation catches this

---

## Success Metrics

### Performance
- ✅ Language detection cache hit rate > 80% on repeated content
- ✅ No connection leaks under 1000+ request load test
- ✅ Configuration validation adds < 100ms to startup time

### Security
- ✅ Webhook signature verification mandatory in production
- ✅ Invalid signatures rejected with 401
- ✅ No security warnings in production mode

### Quality
- ✅ All new code has ≥80% test coverage
- ✅ All tests pass in CI/CD
- ✅ No linting or type errors

### Developer Experience
- ✅ Clear error messages for misconfigurations
- ✅ Comprehensive documentation for rate limiting
- ✅ Configuration summary logged at startup

---

## Rollback Plan

If any critical issue arises:

1. **Issue #6** - Set `FIRECRAWL_WEBHOOK_SECRET` in environment, restart
2. **Issue #1** - Revert lifespan changes, restart application
3. **Issue #4** - Set `LANGUAGE_DETECTION_CACHE_SIZE=0` to disable
4. **Issue #9** - Set `SKIP_CONFIG_VALIDATION=true` (emergency flag)

---

## Post-Implementation

### Monitoring
- Track webhook signature verification failures
- Monitor language detection cache hit rates
- Alert on configuration validation failures

### Future Improvements
- Move rate limiting to Redis for multi-instance support
- Add Prometheus metrics for cache performance
- Implement dynamic configuration reloading

---

## Notes for Implementation

- All changes follow TDD methodology (tests first)
- Maintain backward compatibility for DEBUG mode
- Use feature flags where appropriate
- Add comprehensive logging for troubleshooting
- Document breaking changes in CHANGELOG.md

---

**Ready to implement!** Start with Phase 1 and work through sequentially.
