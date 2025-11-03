"""
Resilience patterns: Retry logic and Circuit Breaker for external service calls.

Implements:
- Exponential backoff retry with jitter
- Circuit breaker pattern to prevent cascading failures
- Configurable retry policies per service
"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast
from dataclasses import dataclass, field
import random

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # Add jitter: random value between 0 and 25% of delay
            delay += random.uniform(0, delay * 0.25)

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

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_attempts = 0

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_attempts = 0
        logger.info(f"🔄 Circuit breaker '{self.name}' reset to CLOSED")

    def record_success(self) -> None:
        """Record successful request."""
        if self.state == CircuitState.HALF_OPEN:
            # Service recovered, close circuit
            self.reset()
            logger.info(f"✅ Circuit breaker '{self.name}' recovered")
        else:
            # In CLOSED state, reset failure count on success
            self.failure_count = 0

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

        except Exception as e:
            last_exception = e

            # Don't retry if circuit breaker is open
            if circuit_breaker and circuit_breaker.get_state() == CircuitState.OPEN:
                logger.error(f"Circuit breaker open, not retrying: {e}")
                raise

            # Don't retry on last attempt
            if attempt == policy.max_attempts - 1:
                logger.error(
                    f"❌ All {policy.max_attempts} retry attempts exhausted: {e}"
                )
                raise

            # Calculate delay and retry
            delay = policy.get_delay(attempt)
            logger.warning(
                f"⚠️ Attempt {attempt + 1}/{policy.max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
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
                func,
                *args,
                policy=policy,
                circuit_breaker=circuit_breaker,
                **kwargs
            )
        return wrapper
    return decorator


# Pre-configured policies for common scenarios
NETWORK_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay=0.5,
    max_delay=5.0,
    exponential_base=1.5,
    jitter=True
)

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.5,
    jitter=True
)


# Global circuit breakers for services (can be accessed across modules)
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    Usage:
        breaker = get_circuit_breaker("firecrawl")
        result = await breaker.execute(api_call, ...)
    """
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig()
        _circuit_breakers[name] = CircuitBreaker(name, config)

    return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (useful for testing)."""
    for breaker in _circuit_breakers.values():
        breaker.reset()
    logger.info("🔄 All circuit breakers reset")
