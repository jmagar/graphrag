"""
TEI (Text Embeddings Inference) service for generating embeddings.
"""

import httpx
import logging
from typing import List, Optional
from app.core.config import settings
from app.core.resilience import (
    retry_with_backoff,
    NETWORK_RETRY_POLICY,
    get_circuit_breaker,
    CircuitBreakerConfig,
)

logger = logging.getLogger(__name__)


# Circuit breaker for TEI API calls
TEI_CIRCUIT_BREAKER = get_circuit_breaker(
    "tei",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0, half_open_max_attempts=1),
)


class EmbeddingsService:
    """
    Service for generating text embeddings using TEI.

    Uses persistent HTTP client with connection pooling for better performance.
    """

    def __init__(self):
        self.base_url = settings.TEI_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
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
                logger.info("🔌 TEI client connections closed")
            except Exception as e:
                logger.error(f"Error closing TEI client: {e}")
            finally:
                self._client = None
        else:
            logger.debug("TEI client already closed or not initialized")

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

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with retry logic.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
        """
        client = await self._get_client()

        @retry_with_backoff(NETWORK_RETRY_POLICY, circuit_breaker=TEI_CIRCUIT_BREAKER)
        async def _make_request():
            response = await client.post(
                f"{self.base_url}/embed",
                json={"inputs": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            return response

        response = await _make_request()
        result: List[List[float]] = response.json()
        return result
