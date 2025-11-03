"""
Resilience patterns: Retry logic and Circuit Breaker for external service calls.

Implements:
- Exponential backoff retry with jitter
- Circuit breaker pattern to prevent cascading failures
- Configurable retry policies per service
"""

# Standard library imports
import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, TYPE_CHECKING

# Third-party imports
import httpx

if TYPE_CHECKING:
    from app.core.circuit_breaker_persistence import CircuitBreakerPersistenceBackend

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exception types that should be retried (network/transient errors)
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    httpx.TimeoutException,
    ConnectionError,
    TimeoutError,
    OSError,
)

# Exception types that should NOT be retried (client errors, programming errors)
NON_RETRYABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    httpx.HTTPStatusError,  # HTTP 4xx/5xx should be handled by caller
)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        if self.jitter:
            # Add jitter: random value between 0 and 25% of delay.
            # 25% is a common industry standard to prevent the thundering herd problem,
            # balancing randomness with predictability. See:
            # https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
            jitter_cap = max(0.0, self.max_delay - delay)
            jitter_span = min(delay * 0.25, jitter_cap)
            if jitter_span > 0:
                delay += random.uniform(0, jitter_span)

        return delay


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Open circuit after N failures
    recovery_timeout: float = 60.0  # seconds to wait before trying again
    half_open_max_attempts: int = 1  # Test requests in half-open state


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests

    Usage:
        breaker = CircuitBreaker(name="firecrawl", config=CircuitBreakerConfig())

        result = await breaker.execute(async_function, *args, **kwargs)
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        persistence_backend: Optional["CircuitBreakerPersistenceBackend"] = None,
    ):
        self.name = name
        self.config = config
        self.persistence_backend = persistence_backend
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_attempts = 0

        # Load state from persistence if available
        # Note: This is synchronous __init__, so we can't await here.
        # State will be loaded lazily on first can_attempt() call.
        self._state_loaded = False

    async def load_from_backend(self) -> None:
        """Load circuit breaker state from persistence backend."""
        if not self.persistence_backend:
            return

        try:
            state_data = await self.persistence_backend.load_state(self.name)
            if state_data:
                # Restore state
                state_str = state_data.get("state", "closed")
                self.state = CircuitState(state_str)
                self.failure_count = state_data.get("failure_count", 0)
                self.last_failure_time = state_data.get("opened_at")
                self.half_open_attempts = state_data.get("half_open_attempts", 0)
                logger.info(
                    f"Loaded circuit breaker '{self.name}' state: {self.state.value}, "
                    f"failures: {self.failure_count}"
                )
        except Exception as e:
            logger.warning(f"Failed to load circuit breaker state for {self.name}: {e}")

        self._state_loaded = True

    async def sync_to_backend(self) -> None:
        """Persist current circuit breaker state to backend."""
        if not self.persistence_backend:
            return

        try:
            state_data = {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "opened_at": self.last_failure_time,
                "half_open_attempts": self.half_open_attempts,
            }
            await self.persistence_backend.save_state(self.name, state_data)
        except Exception as e:
            logger.warning(f"Failed to sync circuit breaker state for {self.name}: {e}")

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_attempts = 0
        logger.info(f"🔄 Circuit breaker '{self.name}' reset to CLOSED")

        # Sync to backend (fire and forget)
        if self.persistence_backend:
            asyncio.create_task(self.sync_to_backend())

    def record_success(self) -> None:
        """Record successful request."""
        if self.state == CircuitState.HALF_OPEN:
            # Service recovered, close circuit
            self.reset()
            logger.info(f"✅ Circuit breaker '{self.name}' recovered")
        else:
            # In CLOSED state, reset failure count on success
            self.failure_count = 0
            # Sync to backend
            if self.persistence_backend:
                asyncio.create_task(self.sync_to_backend())

    def record_failure(self) -> None:
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"🚨 Circuit breaker '{self.name}' OPEN after {self.failure_count} failures"
                )
        elif self.state == CircuitState.HALF_OPEN:
            # Failed again during recovery test, reopen circuit
            self.state = CircuitState.OPEN
            logger.warning(f"🚨 Circuit breaker '{self.name}' reopened after failed test")

        # Sync to backend
        if self.persistence_backend:
            asyncio.create_task(self.sync_to_backend())

    def can_attempt(self) -> bool:
        """Check if request should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.last_failure_time is None:
                return True

            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                # Try recovery
                self.state = CircuitState.HALF_OPEN
                self.half_open_attempts = 0
                logger.info(f"🔄 Circuit breaker '{self.name}' entering HALF_OPEN state")
                return True

            return False

        # HALF_OPEN state: allow limited attempts
        if self.half_open_attempts < self.config.half_open_max_attempts:
            self.half_open_attempts += 1
            return True

        return False

    async def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.

        Raises:
            RuntimeError: If circuit is open
        """
        # Load state from backend on first use
        if not self._state_loaded and self.persistence_backend:
            await self.load_from_backend()

        if not self.can_attempt():
            raise RuntimeError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable (retry in {self.config.recovery_timeout}s)"
            )

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    **kwargs: Any,
) -> Any:
    """
    Execute async function with exponential backoff retry.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        policy: Retry policy configuration (default: 3 attempts, 1s base delay)
        circuit_breaker: Optional circuit breaker for failure protection
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries exhausted

    Example:
        result = await retry_with_backoff(
            api_client.get_data,
            url="https://api.example.com",
            policy=RetryPolicy(max_attempts=5, base_delay=2.0)
        )
    """
    if policy is None:
        policy = RetryPolicy()

    last_exception: Optional[Exception] = None

    for attempt in range(policy.max_attempts):
        try:
            # Use circuit breaker if provided
            if circuit_breaker:
                return await circuit_breaker.execute(func, *args, **kwargs)
            else:
                return await func(*args, **kwargs)

        except NON_RETRYABLE_EXCEPTIONS:
            # Don't retry on non-retryable exceptions (client errors, programming errors)
            logger.error("❌ Non-retryable exception, failing immediately")
            raise

        except RETRYABLE_EXCEPTIONS as e:
            # Retry on network/transient errors
            last_exception = e

            # Don't retry if circuit breaker is open
            if circuit_breaker and circuit_breaker.get_state() == CircuitState.OPEN:
                logger.error(f"Circuit breaker open, not retrying: {e}")
                raise

            # Don't retry on last attempt
            if attempt == policy.max_attempts - 1:
                logger.error(f"❌ All {policy.max_attempts} retry attempts exhausted: {e}")
                raise

            # Calculate delay and retry
            delay = policy.get_delay(attempt)
            logger.warning(
                f"⚠️ Attempt {attempt + 1}/{policy.max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

        except asyncio.CancelledError:
            # Let cancellation propagate immediately - this is a control flow signal
            raise

        except Exception as e:
            # Unknown exceptions - log and retry (conservative approach)
            last_exception = e
            logger.warning(f"⚠️ Unknown exception type {type(e).__name__}, retrying: {e}")

            if attempt == policy.max_attempts - 1:
                logger.error(f"❌ All {policy.max_attempts} retry attempts exhausted: {e}")
                raise

            delay = policy.get_delay(attempt)
            await asyncio.sleep(delay)

    # Should never reach here, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error: no exception to raise")


def with_retry(
    policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
):
    """
    Decorator to add retry logic to async functions.

    Usage:
        @with_retry(policy=RetryPolicy(max_attempts=5))
        async def fetch_data(url: str) -> dict:
            response = await client.get(url)
            return response.json()
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_with_backoff(
                func, *args, policy=policy, circuit_breaker=circuit_breaker, **kwargs
            )

        return wrapper

    return decorator


# Pre-configured policies for common scenarios
NETWORK_RETRY_POLICY = RetryPolicy(
    max_attempts=3, base_delay=1.0, max_delay=10.0, exponential_base=2.0, jitter=True
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=5, base_delay=0.5, max_delay=5.0, exponential_base=1.5, jitter=True
)

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=2, base_delay=2.0, max_delay=30.0, exponential_base=2.5, jitter=True
)


# Global circuit breakers for services (can be accessed across modules)
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    redis_client: Optional[Any] = None,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    Args:
        name: Circuit breaker name
        config: Optional circuit breaker configuration
        redis_client: Optional Redis client for persistence

    Usage:
        breaker = get_circuit_breaker("firecrawl")
        result = await breaker.execute(api_call, ...)

    Note:
        If ENABLE_CIRCUIT_BREAKER_PERSISTENCE is True and redis_client is provided,
        the circuit breaker will persist its state to Redis.
    """
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig()

        # Create persistence backend if enabled and Redis is available
        persistence_backend = None
        try:
            from app.core.config import settings

            if settings.ENABLE_CIRCUIT_BREAKER_PERSISTENCE and redis_client:
                from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend

                persistence_backend = RedisCircuitBreakerBackend(redis_client)
                logger.info(f"Circuit breaker '{name}' using Redis persistence")
        except Exception as e:
            logger.warning(f"Failed to initialize circuit breaker persistence: {e}")

        _circuit_breakers[name] = CircuitBreaker(name, config, persistence_backend)

    return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (useful for testing)."""
    for breaker in _circuit_breakers.values():
        breaker.reset()
    logger.info("🔄 All circuit breakers reset")
