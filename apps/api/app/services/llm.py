"""
LLM service for generating responses using Ollama.
"""

import httpx
import logging
from typing import Optional
from app.core.config import settings
from app.core.resilience import (
    retry_with_backoff,
    NETWORK_RETRY_POLICY,
    get_circuit_breaker,
    CircuitBreakerConfig,
)

logger = logging.getLogger(__name__)


# Circuit breaker for Ollama API calls
OLLAMA_CIRCUIT_BREAKER = get_circuit_breaker(
    "ollama",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0, half_open_max_attempts=1),
)


class LLMService:
    """
    Service for interacting with Ollama LLM.

    Uses persistent HTTP client with connection pooling for better performance.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=10,
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
                logger.info("🔌 Ollama client connections closed")
            except Exception as e:
                logger.error(f"Error closing Ollama client: {e}")
            finally:
                self._client = None
        else:
            logger.debug("Ollama client already closed or not initialized")

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

    async def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a response using the LLM based on the query and context.

        Args:
            query: User's question
            context: Retrieved context from vector database
            system_prompt: Optional custom system prompt

        Returns:
            Generated response text

        Raises:
            ValueError: If OLLAMA_URL is not configured
            httpx.HTTPError: On HTTP errors after retries exhausted
        """
        if not self.base_url:
            raise ValueError(
                "OLLAMA_URL is not configured. Set the OLLAMA_URL environment variable to use LLM features."
            )

        default_system = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "If the context doesn't contain enough information to answer the question, "
            "say so honestly. Always cite sources when possible."
        )

        prompt = f"""Context:
{context}

Question: {query}

Answer based on the context above:"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or default_system,
            "stream": False,
        }

        client = await self._get_client()

        @retry_with_backoff(NETWORK_RETRY_POLICY, circuit_breaker=OLLAMA_CIRCUIT_BREAKER)
        async def _make_request():
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            return response

        response = await _make_request()
        result = response.json()
        llm_response: str = result.get("response", "No response generated")
        return llm_response
