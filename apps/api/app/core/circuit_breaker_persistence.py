"""
Circuit breaker persistence backends for state recovery across restarts.

Provides Redis-backed persistence to ensure circuit breaker state survives
application restarts, preventing immediate failures when services are still down.
"""

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CircuitBreakerPersistenceBackend:
    """Base class for circuit breaker persistence."""

    async def save_state(self, name: str, state: Dict[str, Any]) -> None:
        """
        Save circuit breaker state.

        Args:
            name: Circuit breaker name
            state: State dictionary containing state, failure_count, etc.
        """
        raise NotImplementedError

    async def load_state(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load circuit breaker state.

        Args:
            name: Circuit breaker name

        Returns:
            State dictionary or None if not found
        """
        raise NotImplementedError

    async def delete_state(self, name: str) -> None:
        """
        Delete circuit breaker state.

        Args:
            name: Circuit breaker name
        """
        raise NotImplementedError


class RedisCircuitBreakerBackend(CircuitBreakerPersistenceBackend):
    """Redis-backed circuit breaker persistence."""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Redis persistence backend.

        Args:
            redis_client: Redis async client instance
        """
        self.redis = redis_client

    def _get_key(self, name: str) -> str:
        """
        Get Redis key for circuit breaker state.

        Args:
            name: Circuit breaker name

        Returns:
            Redis key
        """
        return f"circuit_breaker:{name}:state"

    async def save_state(self, name: str, state: Dict[str, Any]) -> None:
        """
        Save circuit breaker state to Redis.

        Args:
            name: Circuit breaker name
            state: State dictionary to persist

        Note:
            Failures are logged but not raised - persistence errors should not
            break the circuit breaker functionality.
        """
        try:
            key = self._get_key(name)
            # Store as JSON for easy debugging
            serialized = json.dumps(state)

            # Set TTL based on state:
            # - OPEN: 24 hours (service might be down for a while)
            # - CLOSED: 1 hour (normal operation, can expire)
            # - HALF_OPEN: 1 hour (transient state)
            ttl = 86400 if state.get("state") == "open" else 3600

            await self.redis.set(key, serialized, ex=ttl)
            logger.debug(f"Persisted circuit breaker state for {name}: {state}")
        except Exception as e:
            logger.warning(f"Failed to persist circuit breaker state for {name}: {e}")
            # Don't raise - persistence failure shouldn't break the app

    async def load_state(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load circuit breaker state from Redis.

        Args:
            name: Circuit breaker name

        Returns:
            State dictionary or None if not found or on error
        """
        try:
            key = self._get_key(name)
            data = await self.redis.get(key)
            if data:
                state = json.loads(data)
                logger.info(f"Loaded circuit breaker state for {name}: {state}")
                return state
            return None
        except Exception as e:
            logger.warning(f"Failed to load circuit breaker state for {name}: {e}")
            return None

    async def delete_state(self, name: str) -> None:
        """
        Delete circuit breaker state from Redis.

        Args:
            name: Circuit breaker name
        """
        try:
            key = self._get_key(name)
            await self.redis.delete(key)
            logger.debug(f"Deleted circuit breaker state for {name}")
        except Exception as e:
            logger.warning(f"Failed to delete circuit breaker state for {name}: {e}")
