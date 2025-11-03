"""
Firecrawl v2 API service with connection pooling and resilience patterns.
"""

import httpx
import logging
from typing import Dict, Any, cast, Optional
from app.core.config import settings
from app.core.resilience import (
    retry_with_backoff,
    NETWORK_RETRY_POLICY,
    get_circuit_breaker,
    CircuitBreakerConfig,
)

logger = logging.getLogger(__name__)


# Circuit breaker for Firecrawl API calls
FIRECRAWL_CIRCUIT_BREAKER = get_circuit_breaker(
    "firecrawl",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0, half_open_max_attempts=1),
)


class FirecrawlService:
    """
    Service for interacting with Firecrawl v2 API.

    Uses persistent HTTP client with connection pooling for better performance.
    """

    def __init__(self):
        self.base_url = settings.FIRECRAWL_URL
        self.api_key = settings.FIRECRAWL_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(60.0, connect=10.0),
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                ),
            )
        return self._client

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

    async def start_crawl(self, crawl_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new crawl using Firecrawl v2 API with retry logic.

        POST /v2/crawl

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
            RuntimeError: If circuit breaker is open
        """

        async def _make_request():
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v2/crawl",
                json=crawl_options,
                timeout=30.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )

    async def get_crawl_status(self, crawl_id: str) -> Dict[str, Any]:
        """
        Get the status of a crawl with retry logic.

        GET /v2/crawl/{id}

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
            RuntimeError: If circuit breaker is open
        """

        async def _make_request():
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/v2/crawl/{crawl_id}",
                timeout=30.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )

    async def cancel_crawl(self, crawl_id: str) -> Dict[str, Any]:
        """
        Cancel a running crawl with retry logic.

        DELETE /v2/crawl/{id}

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
            RuntimeError: If circuit breaker is open
        """

        async def _make_request():
            client = await self._get_client()
            response = await client.delete(
                f"{self.base_url}/v2/crawl/{crawl_id}",
                timeout=30.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )

    async def scrape_url(self, url: str, options: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Scrape a single URL with retry logic.

        POST /v2/scrape

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
            RuntimeError: If circuit breaker is open
        """

        async def _make_request():
            payload = {"url": url}
            if options:
                payload.update(options)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v2/scrape",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )

    async def map_url(self, url: str, options: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Map a website to get all URLs with retry logic.

        POST /v2/map
        """

        async def _make_request():
            payload = {"url": url}
            if options:
                payload.update(options)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v2/map",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )

    async def search_web(self, query: str, options: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Search the web and get full page content with retry logic.

        POST /v2/search
        """

        async def _make_request():
            payload = {"query": query}
            if options:
                payload.update(options)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v2/search",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )

    async def extract_data(
        self, urls: list[str], schema: Dict[str, Any], options: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from webpages with retry logic.

        POST /v2/extract

        Args:
            urls: List of URLs to extract from (Firecrawl v2 API expects array)
            schema: JSON schema describing desired structured output
            options: Additional options including scrapeOptions
        """

        async def _make_request():
            payload = {"urls": urls, "schema": schema}
            if options:
                payload.update(options)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v2/extract",
                json=payload,
                timeout=90.0,
            )
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())

        return await retry_with_backoff(
            _make_request, policy=NETWORK_RETRY_POLICY, circuit_breaker=FIRECRAWL_CIRCUIT_BREAKER
        )
