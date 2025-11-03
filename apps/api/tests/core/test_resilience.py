"""
Tests for resilience patterns: retry logic and circuit breaker.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.resilience import (
    RetryPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    retry_with_backoff,
    with_retry,
    NETWORK_RETRY_POLICY,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)


class TestRetryPolicy:
    """Tests for RetryPolicy configuration."""

    def test_default_policy(self):
        """Test default retry policy values."""
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 30.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True

    def test_get_delay_exponential(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(base_delay=1.0, exponential_base=2.0, jitter=False)

        # Attempt 0: 1.0 * 2^0 = 1.0
        assert policy.get_delay(0) == 1.0

        # Attempt 1: 1.0 * 2^1 = 2.0
        assert policy.get_delay(1) == 2.0

        # Attempt 2: 1.0 * 2^2 = 4.0
        assert policy.get_delay(2) == 4.0

    def test_get_delay_respects_max(self):
        """Test delay respects max_delay cap."""
        policy = RetryPolicy(base_delay=10.0, max_delay=15.0, exponential_base=2.0, jitter=False)

        # Attempt 2 would be 10 * 2^2 = 40, but capped at 15
        assert policy.get_delay(2) == 15.0

    def test_get_delay_with_jitter(self):
        """Test jitter adds randomness to delay."""
        policy = RetryPolicy(base_delay=2.0, jitter=True)

        delays = [policy.get_delay(0) for _ in range(10)]

        # All delays should be >= base_delay (2.0)
        assert all(d >= 2.0 for d in delays)

        # At least some delays should differ (jitter adds randomness)
        assert len(set(delays)) > 1


class TestCircuitBreaker:
    """Tests for CircuitBreaker pattern."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test", config)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.can_attempt() is True

    def test_opens_after_threshold_failures(self):
        """Test circuit opens after reaching failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        # Record failures
        breaker.record_failure()  # 1
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()  # 2
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()  # 3 - should open
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_attempt() is False

    def test_transitions_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        import time
        time.sleep(0.2)

        # Should transition to HALF_OPEN
        assert breaker.can_attempt() is True
        assert breaker.state == CircuitState.HALF_OPEN

    def test_closes_on_success_in_half_open(self):
        """Test circuit closes after successful request in HALF_OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Wait and transition to HALF_OPEN
        import time
        time.sleep(0.2)
        breaker.can_attempt()

        # Record success - should close circuit
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_reopens_on_failure_in_half_open(self):
        """Test circuit reopens if request fails in HALF_OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Wait and transition to HALF_OPEN
        import time
        time.sleep(0.2)
        breaker.can_attempt()
        assert breaker.state == CircuitState.HALF_OPEN

        # Record failure - should reopen
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_reset_closes_circuit(self):
        """Test reset() closes circuit and clears failures."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.can_attempt() is True

    @pytest.mark.anyio
    async def test_execute_with_success(self):
        """Test execute() with successful function call."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test", config)

        async def success_func():
            return "success"

        result = await breaker.execute(success_func)
        assert result == "success"
        assert breaker.failure_count == 0

    @pytest.mark.anyio
    async def test_execute_with_failure(self):
        """Test execute() records failure and raises exception."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        async def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await breaker.execute(failing_func)

        assert breaker.failure_count == 1

    @pytest.mark.anyio
    async def test_execute_rejects_when_open(self):
        """Test execute() rejects requests when circuit is OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        async def any_func():
            return "should not execute"

        with pytest.raises(RuntimeError, match="Circuit breaker .* is OPEN"):
            await breaker.execute(any_func)


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.anyio
    async def test_succeeds_on_first_attempt(self):
        """Test function succeeds without retries."""
        mock_func = AsyncMock(return_value="success")
        policy = RetryPolicy(max_attempts=3, base_delay=0.1)

        result = await retry_with_backoff(mock_func, policy=policy)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.anyio
    async def test_retries_on_failure(self):
        """Test function retries on failure."""
        mock_func = AsyncMock(side_effect=[
            ConnectionError("fail 1"),
            ConnectionError("fail 2"),
            "success"
        ])
        policy = RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False)

        result = await retry_with_backoff(mock_func, policy=policy)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.anyio
    async def test_exhausts_retries_and_raises(self):
        """Test raises last exception when all retries exhausted."""
        mock_func = AsyncMock(side_effect=ConnectionError("persistent error"))
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)

        with pytest.raises(ConnectionError, match="persistent error"):
            await retry_with_backoff(mock_func, policy=policy)

        assert mock_func.call_count == 3

    @pytest.mark.anyio
    async def test_respects_circuit_breaker(self):
        """Test retry respects circuit breaker state."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)

        mock_func = AsyncMock(side_effect=ConnectionError("error"))
        policy = RetryPolicy(max_attempts=5, base_delay=0.01)

        with pytest.raises(ConnectionError):
            await retry_with_backoff(mock_func, policy=policy, circuit_breaker=breaker)

        # Circuit should be open after 2 failures
        assert breaker.state == CircuitState.OPEN

        # Further attempts should be rejected immediately
        with pytest.raises(RuntimeError, match="Circuit breaker .* is OPEN"):
            await retry_with_backoff(mock_func, policy=policy, circuit_breaker=breaker)

    @pytest.mark.anyio
    async def test_passes_args_and_kwargs(self):
        """Test function receives correct arguments."""
        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        policy = RetryPolicy(max_attempts=1)
        result = await retry_with_backoff(func_with_args, 1, 2, c=3, policy=policy)

        assert result == "1-2-3"


class TestWithRetryDecorator:
    """Tests for @with_retry decorator."""

    @pytest.mark.anyio
    async def test_decorator_applies_retry(self):
        """Test decorator adds retry behavior to function."""
        call_count = 0

        @with_retry(policy=RetryPolicy(max_attempts=3, base_delay=0.01))
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("not yet")
            return "success"

        result = await flaky_function()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.anyio
    async def test_decorator_with_circuit_breaker(self):
        """Test decorator works with circuit breaker."""
        breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))

        @with_retry(policy=RetryPolicy(max_attempts=5, base_delay=0.01), circuit_breaker=breaker)
        async def always_fails():
            raise ConnectionError("error")

        with pytest.raises(ConnectionError):
            await always_fails()

        # Circuit should be open
        assert breaker.state == CircuitState.OPEN


class TestPredefinedPolicies:
    """Tests for predefined retry policies."""

    def test_network_retry_policy(self):
        """Test NETWORK_RETRY_POLICY configuration."""
        assert NETWORK_RETRY_POLICY.max_attempts == 3
        assert NETWORK_RETRY_POLICY.base_delay == 1.0
        assert NETWORK_RETRY_POLICY.max_delay == 10.0

    def test_get_circuit_breaker_creates_new(self):
        """Test get_circuit_breaker() creates new breaker."""
        reset_all_circuit_breakers()  # Clean slate

        breaker = get_circuit_breaker("new_service")
        assert breaker.name == "new_service"
        assert breaker.state == CircuitState.CLOSED

    def test_get_circuit_breaker_returns_existing(self):
        """Test get_circuit_breaker() returns existing breaker."""
        reset_all_circuit_breakers()

        breaker1 = get_circuit_breaker("service")
        breaker1.record_failure()

        breaker2 = get_circuit_breaker("service")
        assert breaker2 is breaker1
        assert breaker2.failure_count == 1

    def test_reset_all_circuit_breakers(self):
        """Test reset_all_circuit_breakers() resets all breakers."""
        reset_all_circuit_breakers()

        breaker1 = get_circuit_breaker("service1")
        breaker2 = get_circuit_breaker("service2")

        breaker1.record_failure()
        breaker2.record_failure()

        reset_all_circuit_breakers()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED


class TestCircuitBreakerPersistence:
    """Tests for circuit breaker persistence backend."""

    @pytest.mark.anyio
    async def test_persistence_backend_save_and_load(self):
        """Test persistence backend can save and load circuit breaker state."""
        from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend
        from unittest.mock import AsyncMock

        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"state": "open", "failure_count": 5}')
        mock_redis.delete = AsyncMock()

        backend = RedisCircuitBreakerBackend(mock_redis)

        # Test save_state
        state = {"state": "open", "failure_count": 5}
        await backend.save_state("test_service", state)
        mock_redis.set.assert_called_once()

        # Test load_state
        loaded_state = await backend.load_state("test_service")
        assert loaded_state == state
        mock_redis.get.assert_called_once()

        # Test delete_state
        await backend.delete_state("test_service")
        mock_redis.delete.assert_called_once()

    @pytest.mark.anyio
    async def test_circuit_breaker_with_persistence_loads_state(self):
        """Test CircuitBreaker loads state from persistence backend on initialization."""
        from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend
        from unittest.mock import AsyncMock

        # Mock Redis client with OPEN state
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value='{"state": "open", "failure_count": 5, "opened_at": 1234567890.0}')

        backend = RedisCircuitBreakerBackend(mock_redis)

        # Create circuit breaker with persistence
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test_service", config, persistence_backend=backend)

        # Load state from backend (since __init__ is synchronous)
        await breaker.load_from_backend()

        # Verify state was loaded
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 5

    @pytest.mark.anyio
    async def test_circuit_breaker_persists_state_changes(self):
        """Test CircuitBreaker persists state changes to backend."""
        from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend
        from unittest.mock import AsyncMock
        import asyncio

        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)  # No initial state
        mock_redis.set = AsyncMock()

        backend = RedisCircuitBreakerBackend(mock_redis)

        # Create circuit breaker with persistence
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test_service", config, persistence_backend=backend)

        # Record failures to open circuit
        breaker.record_failure()
        breaker.record_failure()

        # Wait for background tasks to complete
        await asyncio.sleep(0.1)

        # Verify state was persisted (called after each state change)
        assert mock_redis.set.call_count >= 1
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.anyio
    async def test_persistence_backend_handles_redis_errors_gracefully(self):
        """Test persistence backend handles Redis errors without breaking circuit breaker."""
        from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend
        from unittest.mock import AsyncMock

        # Mock Redis client that fails
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

        backend = RedisCircuitBreakerBackend(mock_redis)

        # Should not raise - just log warning
        await backend.save_state("test", {"state": "closed"})
        result = await backend.load_state("test")

        # Should return None on error
        assert result is None

    @pytest.mark.anyio
    async def test_circuit_breaker_works_without_persistence(self):
        """Test CircuitBreaker works normally without persistence backend."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test_service", config, persistence_backend=None)

        # Should work normally
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
