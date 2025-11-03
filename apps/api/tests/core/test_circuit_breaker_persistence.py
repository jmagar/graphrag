"""
Tests for Redis-backed circuit breaker persistence.

This module tests the RedisCircuitBreakerBackend class which provides
persistent storage for circuit breaker state, allowing circuit breakers
to survive application restarts and share state across instances.

TDD Approach: These tests are written first (RED phase) before implementation.
"""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from fakeredis import FakeAsyncRedis


# Import will fail initially since features don't exist yet
# This is expected in TDD - tests are written first
try:
    from app.core.circuit_breaker_persistence import RedisCircuitBreakerBackend
except ImportError:
    # Create a placeholder class for testing purposes
    class RedisCircuitBreakerBackend:
        """Placeholder class - will be implemented to make tests pass."""
        pass


from app.core.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitState


@pytest.mark.asyncio
class TestRedisCircuitBreakerBackend:
    """Test suite for Redis-backed circuit breaker persistence."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def redis_backend(self, fake_redis):
        """Create RedisCircuitBreakerBackend with fake Redis."""
        backend = RedisCircuitBreakerBackend(redis_client=fake_redis)
        yield backend

    async def test_backend_initialization(self, fake_redis):
        """Test RedisCircuitBreakerBackend can be initialized."""
        backend = RedisCircuitBreakerBackend(redis_client=fake_redis)
        assert backend is not None
        assert hasattr(backend, "redis")

    async def test_save_state_stores_in_redis(self, redis_backend, fake_redis):
        """Test saving circuit breaker state to Redis."""
        service_name = "test_service"
        state_data = {
            "state": "OPEN",
            "failure_count": 5,
            "last_failure_time": 1234567890.0,
            "half_open_attempts": 0,
        }

        await redis_backend.save_state(service_name, state_data)

        # Verify data was stored
        stored_key = f"circuit_breaker:{service_name}:state"
        exists = await fake_redis.exists(stored_key)
        assert exists == 1

    async def test_load_state_retrieves_from_redis(self, redis_backend, fake_redis):
        """Test loading circuit breaker state from Redis."""
        service_name = "test_service"
        state_data = {
            "state": "OPEN",
            "failure_count": 5,
            "last_failure_time": 1234567890.0,
        }

        # Save state
        await redis_backend.save_state(service_name, state_data)

        # Load state
        loaded_state = await redis_backend.load_state(service_name)

        assert loaded_state is not None
        assert loaded_state["state"] == "OPEN"
        assert loaded_state["failure_count"] == 5
        assert loaded_state["last_failure_time"] == 1234567890.0

    async def test_load_state_returns_none_when_not_found(self, redis_backend):
        """Test loading non-existent state returns None."""
        loaded_state = await redis_backend.load_state("nonexistent_service")
        assert loaded_state is None

    async def test_delete_state_removes_from_redis(self, redis_backend, fake_redis):
        """Test deleting circuit breaker state from Redis."""
        service_name = "test_service"
        state_data = {"state": "CLOSED", "failure_count": 0}

        # Save state
        await redis_backend.save_state(service_name, state_data)

        # Delete state
        await redis_backend.delete_state(service_name)

        # Verify deleted
        loaded = await redis_backend.load_state(service_name)
        assert loaded is None

    async def test_save_state_with_ttl(self, redis_backend, fake_redis):
        """Test saving state with TTL expiration."""
        service_name = "test_service"
        state_data = {"state": "OPEN", "failure_count": 3}
        ttl_seconds = 60

        await redis_backend.save_state(service_name, state_data)

        # Check TTL was set
        stored_key = f"circuit_breaker:{service_name}:state"
        ttl = await fake_redis.ttl(stored_key)
        assert ttl > 0

    async def test_state_persistence_handles_all_circuit_states(self, redis_backend):
        """Test persistence works with all circuit states."""
        test_states = [
            {"state": "CLOSED", "failure_count": 0},
            {"state": "OPEN", "failure_count": 5},
            {"state": "HALF_OPEN", "failure_count": 5, "half_open_attempts": 1},
        ]

        for state_data in test_states:
            service_name = f"service_{state_data['state']}"
            await redis_backend.save_state(service_name, state_data)
            loaded = await redis_backend.load_state(service_name)
            assert loaded["state"] == state_data["state"]

    async def test_concurrent_save_operations(self, redis_backend):
        """Test multiple concurrent save operations don't corrupt data."""
        import asyncio

        async def save_state(service_name: str, failure_count: int):
            state_data = {"state": "CLOSED", "failure_count": failure_count}
            await redis_backend.save_state(service_name, state_data)

        # Save multiple states concurrently
        await asyncio.gather(
            save_state("service1", 1),
            save_state("service2", 2),
            save_state("service3", 3),
        )

        # Verify all states were saved correctly
        state1 = await redis_backend.load_state("service1")
        state2 = await redis_backend.load_state("service2")
        state3 = await redis_backend.load_state("service3")

        assert state1["failure_count"] == 1
        assert state2["failure_count"] == 2
        assert state3["failure_count"] == 3

    async def test_redis_connection_failure_handling(self, redis_backend):
        """Test graceful handling of Redis connection failures."""
        # Simulate Redis unavailability
        redis_backend.redis = None

        # Should not raise exception, but log warning
        await redis_backend.save_state("test", {"state": "OPEN"})
        # Implementation handles gracefully - no exception raised

    @pytest.mark.skip(reason="list_all() method not yet implemented")
    async def test_list_all_circuit_breakers(self, redis_backend):
        """Test listing all circuit breakers with their states."""
        # Save multiple circuit breaker states
        await redis_backend.save_state("service1", {"state": "CLOSED"})
        await redis_backend.save_state("service2", {"state": "OPEN"})
        await redis_backend.save_state("service3", {"state": "HALF_OPEN"})

        # List all
        all_breakers = await redis_backend.list_all()

        assert len(all_breakers) >= 3
        service_names = [b["name"] for b in all_breakers]
        assert "service1" in service_names
        assert "service2" in service_names
        assert "service3" in service_names


@pytest.mark.asyncio
class TestCircuitBreakerWithPersistence:
    """Test CircuitBreaker integration with persistence backend."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def redis_backend(self, fake_redis):
        """Create persistence backend."""
        return RedisCircuitBreakerBackend(redis_client=fake_redis)

    @pytest_asyncio.fixture
    async def persistent_circuit_breaker(self, redis_backend):
        """Create circuit breaker with persistence backend."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
        breaker = CircuitBreaker(
            name="test_service",
            config=config,
            persistence_backend=redis_backend
        )
        return breaker

    async def test_circuit_breaker_loads_state_on_init(self, redis_backend):
        """Test circuit breaker loads persisted state on initialization."""
        # Pre-populate Redis with OPEN state
        service_name = "test_service"
        await redis_backend.save_state(service_name, {
            "state": "open",
            "failure_count": 5,
            "opened_at": time.time(),
        })

        # Create circuit breaker
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(
            name=service_name,
            config=config,
            persistence_backend=redis_backend
        )

        # Explicitly load state (would normally happen on first execute())
        await breaker.load_from_backend()

        # Verify state was loaded
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 5

    async def test_circuit_breaker_persists_state_on_failure(self, persistent_circuit_breaker, redis_backend):
        """Test circuit breaker persists state after recording failure."""
        # Record failure
        persistent_circuit_breaker.record_failure()

        # Explicitly sync to backend (normally done async via create_task)
        await persistent_circuit_breaker.sync_to_backend()

        # Verify state was persisted
        saved_state = await redis_backend.load_state("test_service")
        assert saved_state is not None
        assert saved_state["failure_count"] == 1

    async def test_circuit_breaker_persists_state_on_success(self, persistent_circuit_breaker, redis_backend):
        """Test circuit breaker persists state after recording success."""
        # Record failure then success
        persistent_circuit_breaker.record_failure()
        persistent_circuit_breaker.record_success()

        # Explicitly sync to backend
        await persistent_circuit_breaker.sync_to_backend()

        # Verify state was persisted with reset failure count
        saved_state = await redis_backend.load_state("test_service")
        assert saved_state is not None
        assert saved_state["failure_count"] == 0

    async def test_state_survives_restart_simulation(self, redis_backend):
        """Test circuit breaker state survives restart (create new instance)."""
        service_name = "persistent_service"
        config = CircuitBreakerConfig(failure_threshold=2)

        # First instance - record failures
        breaker1 = CircuitBreaker(
            name=service_name,
            config=config,
            persistence_backend=redis_backend
        )
        breaker1.record_failure()
        breaker1.record_failure()
        assert breaker1.state == CircuitState.OPEN

        # Explicitly sync to persist state
        await breaker1.sync_to_backend()

        # Simulate restart - create new instance with same name
        breaker2 = CircuitBreaker(
            name=service_name,
            config=config,
            persistence_backend=redis_backend
        )

        # Explicitly load state (normally happens on first execute())
        await breaker2.load_from_backend()

        # Should load OPEN state from Redis
        assert breaker2.state == CircuitState.OPEN
        assert breaker2.failure_count == 2

    async def test_circuit_breaker_reset_clears_persistence(self, persistent_circuit_breaker, redis_backend):
        """Test resetting circuit breaker clears persisted state."""
        # Open circuit
        persistent_circuit_breaker.record_failure()
        persistent_circuit_breaker.record_failure()

        # Reset
        persistent_circuit_breaker.reset()

        # Explicitly sync to backend
        await persistent_circuit_breaker.sync_to_backend()

        # Verify persistence was cleared/updated
        saved_state = await redis_backend.load_state("test_service")
        assert saved_state is not None
        assert saved_state["state"] == "closed"
        assert saved_state["failure_count"] == 0

    async def test_multiple_circuit_breakers_independent_state(self, redis_backend):
        """Test multiple circuit breakers maintain independent persisted state."""
        config = CircuitBreakerConfig(failure_threshold=2)

        breaker1 = CircuitBreaker("service1", config, persistence_backend=redis_backend)
        breaker2 = CircuitBreaker("service2", config, persistence_backend=redis_backend)

        # Record different failures
        breaker1.record_failure()
        breaker2.record_failure()
        breaker2.record_failure()

        # Verify independent states
        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.OPEN

        # Explicitly sync both to backend
        await breaker1.sync_to_backend()
        await breaker2.sync_to_backend()

        # Verify persistence
        state1 = await redis_backend.load_state("service1")
        state2 = await redis_backend.load_state("service2")

        assert state1["failure_count"] == 1
        assert state2["failure_count"] == 2

    async def test_persistence_with_half_open_state(self, redis_backend):
        """Test persistence correctly handles HALF_OPEN state transitions."""
        service_name = "half_open_service"
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # Short timeout for testing
            half_open_max_attempts=1
        )

        breaker = CircuitBreaker(service_name, config, persistence_backend=redis_backend)

        # Open circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Attempt request - should transition to HALF_OPEN
        can_attempt = breaker.can_attempt()
        assert can_attempt is True
        assert breaker.state == CircuitState.HALF_OPEN

        # Explicitly sync to backend
        await breaker.sync_to_backend()

        # Verify HALF_OPEN state is persisted
        saved_state = await redis_backend.load_state(service_name)
        assert saved_state["state"] == "half_open"

    async def test_persistence_backend_unavailable_fallback(self, redis_backend):
        """Test circuit breaker operates normally when persistence unavailable."""
        config = CircuitBreakerConfig(failure_threshold=2)

        # Create breaker with working backend
        breaker = CircuitBreaker("test_service", config, persistence_backend=redis_backend)

        # Simulate backend failure
        breaker.persistence_backend.redis = None

        # Circuit breaker should still work (in-memory only)
        breaker.record_failure()
        breaker.record_failure()

        # Should still open circuit even without persistence
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.skip(reason="TTL is auto-determined by state, not configurable")
    async def test_persistence_ttl_expiration(self, redis_backend, fake_redis):
        """Test that expired circuit breaker state is handled correctly."""
        service_name = "ttl_service"

        # Save state - TTL is automatically set based on state (24h OPEN, 1h CLOSED)
        await redis_backend.save_state(
            service_name,
            {"state": "OPEN", "failure_count": 5}
        )

        # Wait for expiration (would need to wait 24h for OPEN state)
        # This test is not practical with auto-TTL
        await asyncio.sleep(1.5)

        # Try to load - should return None after TTL expires
        loaded_state = await redis_backend.load_state(service_name)
        assert loaded_state is None

    async def test_circuit_breaker_execute_with_persistence(self, persistent_circuit_breaker, redis_backend):
        """Test execute() method persists state changes."""
        async def failing_function():
            raise ConnectionError("Test error")

        # Execute failing function
        try:
            await persistent_circuit_breaker.execute(failing_function)
        except ConnectionError:
            pass

        # Explicitly sync to backend
        await persistent_circuit_breaker.sync_to_backend()

        # Verify failure was persisted
        saved_state = await redis_backend.load_state("test_service")
        assert saved_state["failure_count"] == 1


@pytest.mark.asyncio
class TestRedisUnavailabilityScenarios:
    """Test graceful degradation when Redis is unavailable."""

    async def test_backend_creation_with_unavailable_redis(self):
        """Test backend handles Redis connection failure gracefully."""
        # Create backend with invalid Redis connection
        fake_redis = MagicMock()
        fake_redis.ping = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

        backend = RedisCircuitBreakerBackend(redis_client=fake_redis)

        # Should not raise exception
        assert backend is not None

    async def test_save_state_fails_gracefully(self):
        """Test save_state handles Redis errors gracefully."""
        fake_redis = MagicMock()
        fake_redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))

        backend = RedisCircuitBreakerBackend(redis_client=fake_redis)

        # Should not raise exception, just log warning
        await backend.save_state("test", {"state": "OPEN"})
        # No assertion - just verifying no exception raised

    async def test_load_state_fails_gracefully(self):
        """Test load_state handles Redis errors gracefully."""
        fake_redis = MagicMock()
        fake_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))

        backend = RedisCircuitBreakerBackend(redis_client=fake_redis)

        # Should return None, not raise exception
        result = await backend.load_state("test")
        assert result is None

    async def test_circuit_breaker_works_without_persistence(self):
        """Test circuit breaker functions normally without persistence backend."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)  # No persistence backend

        # Should work normally
        breaker.record_failure()
        breaker.record_failure()

        assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
class TestPersistencePerformance:
    """Test persistence performance characteristics."""

    @pytest_asyncio.fixture
    async def fake_redis(self):
        """Create a fake Redis instance for testing."""
        redis = FakeAsyncRedis(decode_responses=True)
        yield redis
        await redis.flushall()
        await redis.aclose()

    @pytest_asyncio.fixture
    async def redis_backend(self, fake_redis):
        """Create persistence backend."""
        return RedisCircuitBreakerBackend(redis_client=fake_redis)

    async def test_save_performance(self, redis_backend):
        """Test save operation completes within acceptable time."""
        import time

        state_data = {
            "state": "OPEN",
            "failure_count": 5,
            "last_failure_time": time.time(),
        }

        start = time.time()
        await redis_backend.save_state("test_service", state_data)
        elapsed = time.time() - start

        # Should complete in under 100ms (fakeredis is fast)
        assert elapsed < 0.1, f"Save took {elapsed:.3f}s, expected <0.1s"

    async def test_load_performance(self, redis_backend):
        """Test load operation completes within acceptable time."""
        import time

        # Pre-populate
        await redis_backend.save_state("test_service", {"state": "OPEN"})

        start = time.time()
        await redis_backend.load_state("test_service")
        elapsed = time.time() - start

        # Should complete in under 100ms
        assert elapsed < 0.1, f"Load took {elapsed:.3f}s, expected <0.1s"

    async def test_bulk_operations_performance(self, redis_backend):
        """Test performance with multiple circuit breakers."""
        import time

        # Save 100 circuit breaker states
        start = time.time()
        for i in range(100):
            await redis_backend.save_state(
                f"service_{i}",
                {"state": "CLOSED", "failure_count": i % 5}
            )
        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second for fakeredis)
        assert elapsed < 1.0, f"Bulk save took {elapsed:.3f}s, expected <1s"
