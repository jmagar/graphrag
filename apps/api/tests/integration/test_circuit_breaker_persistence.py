"""
Integration test for circuit breaker persistence with real Redis.

This test demonstrates that circuit breaker state survives "restarts"
by simulating app restart through clearing the in-memory circuit breaker cache.
"""

import pytest
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker,
    _circuit_breakers,
)
from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend
from app.services.redis_service import RedisService
import asyncio


@pytest.mark.anyio
async def test_circuit_breaker_persistence_across_restarts():
    """Test that circuit breaker state persists across simulated restarts."""
    # Initialize Redis service
    redis_service = RedisService()
    redis_available = await redis_service.is_available()

    if not redis_available:
        pytest.skip("Redis not available for integration test")

    # Clean up any existing state
    backend = RedisCircuitBreakerBackend(redis_service.client)
    await backend.delete_state("test_persistence_service")

    try:
        # === STEP 1: First "app instance" - open the circuit ===
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
        breaker1 = CircuitBreaker("test_persistence_service", config, persistence_backend=backend)

        # Circuit should start CLOSED
        assert breaker1.state == CircuitState.CLOSED
        assert breaker1.failure_count == 0

        # Fail 3 times to open circuit
        breaker1.record_failure()
        breaker1.record_failure()
        breaker1.record_failure()

        # Wait for background persistence
        await asyncio.sleep(0.2)

        # Verify circuit is OPEN
        assert breaker1.state == CircuitState.OPEN
        assert breaker1.failure_count == 3

        # === STEP 2: Simulate app restart ===
        # In real life, this would be a new Python process.
        # We simulate by creating a new CircuitBreaker instance.
        breaker2 = CircuitBreaker("test_persistence_service", config, persistence_backend=backend)

        # Before loading from backend, state should be default (CLOSED)
        assert breaker2.state == CircuitState.CLOSED

        # Load state from Redis
        await breaker2.load_from_backend()

        # === VERIFICATION: State should be restored ===
        assert breaker2.state == CircuitState.OPEN, "Circuit state did not persist!"
        assert breaker2.failure_count == 3, "Failure count did not persist!"

        print("\n✅ SUCCESS: Circuit breaker state persisted across restart!")
        print(f"   - State: {breaker2.state.value}")
        print(f"   - Failure count: {breaker2.failure_count}")

        # === STEP 3: Test recovery ===
        # Reset the circuit
        breaker2.reset()
        await asyncio.sleep(0.2)

        # Create third instance to verify reset persisted
        breaker3 = CircuitBreaker("test_persistence_service", config, persistence_backend=backend)
        await breaker3.load_from_backend()

        assert breaker3.state == CircuitState.CLOSED, "Reset did not persist!"
        assert breaker3.failure_count == 0, "Failure count did not reset!"

        print("✅ SUCCESS: Circuit breaker reset persisted!")

    finally:
        # Cleanup
        await backend.delete_state("test_persistence_service")
        await redis_service.close()


@pytest.mark.anyio
async def test_get_circuit_breaker_with_persistence():
    """Test get_circuit_breaker() factory with Redis persistence."""
    redis_service = RedisService()
    redis_available = await redis_service.is_available()

    if not redis_available:
        pytest.skip("Redis not available for integration test")

    # Clean up
    _circuit_breakers.clear()
    backend = RedisCircuitBreakerBackend(redis_service.client)
    await backend.delete_state("factory_test_service")

    try:
        # Get circuit breaker with Redis persistence
        breaker1 = get_circuit_breaker(
            "factory_test_service",
            config=CircuitBreakerConfig(failure_threshold=2),
            redis_client=redis_service.client,
        )

        # Open the circuit
        breaker1.record_failure()
        breaker1.record_failure()
        await asyncio.sleep(0.2)

        assert breaker1.state == CircuitState.OPEN

        # Clear in-memory cache to simulate restart
        _circuit_breakers.clear()

        # Get circuit breaker again (simulates new app instance)
        breaker2 = get_circuit_breaker(
            "factory_test_service",
            config=CircuitBreakerConfig(failure_threshold=2),
            redis_client=redis_service.client,
        )

        # Load state from backend
        await breaker2.load_from_backend()

        # Verify state persisted
        assert breaker2.state == CircuitState.OPEN
        print("\n✅ SUCCESS: get_circuit_breaker() with persistence works!")

    finally:
        # Cleanup
        await backend.delete_state("factory_test_service")
        _circuit_breakers.clear()
        await redis_service.close()
