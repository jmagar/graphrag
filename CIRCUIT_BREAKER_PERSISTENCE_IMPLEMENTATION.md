# Circuit Breaker Persistence Implementation

## Overview

Implemented Redis-backed persistence for circuit breaker state to survive application restarts. This prevents immediate failures when the application restarts if a service was previously OPEN (failing).

## What Was Implemented

### 1. **RedisCircuitBreakerBackend Class**
**File**: `/home/user/graphrag/apps/api/app/core/circuit_breaker_persistence.py`

A new persistence backend that stores circuit breaker state in Redis:

```python
class RedisCircuitBreakerBackend(CircuitBreakerPersistenceBackend):
    """Redis-backed circuit breaker persistence."""

    async def save_state(self, name: str, state: Dict[str, Any]) -> None:
        """Save circuit breaker state to Redis with TTL."""

    async def load_state(self, name: str) -> Optional[Dict[str, Any]]:
        """Load circuit breaker state from Redis."""

    async def delete_state(self, name: str) -> None:
        """Delete circuit breaker state from Redis."""
```

**Key Features**:
- Stores state in Redis keys: `circuit_breaker:{name}:state`
- State includes: `state` (CLOSED/OPEN/HALF_OPEN), `failure_count`, `opened_at`, `half_open_attempts`
- Uses JSON serialization for easy debugging
- TTL-based cleanup:
  - OPEN circuits: 24 hours (service might be down for a while)
  - CLOSED/HALF_OPEN circuits: 1 hour
- Graceful error handling: persistence failures are logged but don't break the circuit breaker

### 2. **Modified CircuitBreaker Class**
**File**: `/home/user/graphrag/apps/api/app/core/resilience.py`

Enhanced the `CircuitBreaker` class to support persistence:

```python
class CircuitBreaker:
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        persistence_backend: Optional[CircuitBreakerPersistenceBackend] = None,
    ):
        # ... initialization code
        self.persistence_backend = persistence_backend
        self._state_loaded = False
```

**New Methods**:
- `async load_from_backend()`: Loads state from Redis on initialization
- `async sync_to_backend()`: Persists current state to Redis

**Modified Methods**:
- `execute()`: Loads state from backend on first use (lazy loading)
- `record_success()`: Syncs state to backend after success
- `record_failure()`: Syncs state to backend after failure
- `reset()`: Syncs state to backend after reset

**Important Design Decisions**:
- Persistence is **non-blocking**: Uses `asyncio.create_task()` for background syncing
- Lazy loading: State is loaded on first `execute()` call (since `__init__` is synchronous)
- Backward compatible: Works without persistence backend

### 3. **Configuration Flag**
**File**: `/home/user/graphrag/apps/api/app/core/config.py`

Added new feature flag:

```python
# Feature Flags
ENABLE_CIRCUIT_BREAKER_PERSISTENCE: bool = False  # Enable Redis-backed circuit breaker state persistence
```

**Default**: `False` (disabled by default for safety)

To enable, add to `.env`:
```bash
ENABLE_CIRCUIT_BREAKER_PERSISTENCE=true
```

### 4. **Updated get_circuit_breaker() Factory**
**File**: `/home/user/graphrag/apps/api/app/core/resilience.py`

Enhanced the factory function to optionally use Redis persistence:

```python
def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    redis_client: Optional[Any] = None,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    If ENABLE_CIRCUIT_BREAKER_PERSISTENCE is True and redis_client is provided,
    the circuit breaker will persist its state to Redis.
    """
```

**Usage**:
```python
from app.services.redis_service import RedisService

redis_service = RedisService()
breaker = get_circuit_breaker(
    "firecrawl",
    redis_client=redis_service.client if await redis_service.is_available() else None
)
```

## Testing

### Unit Tests (29 tests, all passing)
**File**: `/home/user/graphrag/apps/api/tests/core/test_resilience.py`

Added 5 new test cases for persistence:
1. `test_persistence_backend_save_and_load`: Tests basic save/load operations
2. `test_circuit_breaker_with_persistence_loads_state`: Tests state loading on initialization
3. `test_circuit_breaker_persists_state_changes`: Tests that state changes are persisted
4. `test_persistence_backend_handles_redis_errors_gracefully`: Tests error handling
5. `test_circuit_breaker_works_without_persistence`: Tests backward compatibility

All existing tests still pass, ensuring backward compatibility.

### Integration Tests
**File**: `/home/user/graphrag/apps/api/tests/integration/test_circuit_breaker_persistence.py`

Added 2 integration tests that demonstrate persistence across simulated restarts:
1. `test_circuit_breaker_persistence_across_restarts`: Simulates app restart and verifies state persists
2. `test_get_circuit_breaker_with_persistence`: Tests the factory function with Redis persistence

These tests are skipped if Redis is not available.

## How It Works

### Scenario: Service Failure and Recovery

1. **Normal Operation (CLOSED)**:
   - Circuit breaker starts in CLOSED state
   - Requests pass through normally
   - State is synced to Redis: `{"state": "closed", "failure_count": 0, ...}`

2. **Service Fails (OPEN)**:
   - After 5 failures (default threshold), circuit opens
   - State synced to Redis: `{"state": "open", "failure_count": 5, "opened_at": 1234567890.0}`
   - Subsequent requests are rejected immediately

3. **Application Restarts**:
   - New CircuitBreaker instance created
   - On first `execute()` call, state is loaded from Redis
   - Circuit remains OPEN (prevents immediate failures)
   - After recovery timeout, transitions to HALF_OPEN

4. **Service Recovers (HALF_OPEN → CLOSED)**:
   - Test request succeeds
   - Circuit closes
   - State synced to Redis: `{"state": "closed", "failure_count": 0, ...}`

### Without Persistence (Current Behavior)

Without persistence, the circuit breaker would reset to CLOSED on restart, causing:
- Immediate failures when service is still down
- Wasted retries and timeouts
- Poor user experience

### With Persistence (New Behavior)

With persistence, the circuit breaker:
- Remembers it's OPEN across restarts
- Continues rejecting requests immediately
- Only tests recovery after timeout
- Provides consistent behavior

## Usage Examples

### Basic Usage (No Persistence)

```python
from app.core.resilience import get_circuit_breaker

# Without Redis - uses in-memory state only
breaker = get_circuit_breaker("firecrawl")
result = await breaker.execute(api_call)
```

### With Persistence Enabled

```python
from app.core.resilience import get_circuit_breaker
from app.services.redis_service import RedisService

# Initialize Redis
redis_service = RedisService()
redis_available = await redis_service.is_available()

# Create circuit breaker with persistence
breaker = get_circuit_breaker(
    "firecrawl",
    redis_client=redis_service.client if redis_available else None
)

# State will be loaded from Redis on first execute()
result = await breaker.execute(api_call)
```

### Explicit State Loading

```python
# Load state immediately (before first execute)
await breaker.load_from_backend()

# Check state
print(f"Circuit state: {breaker.state.value}")
print(f"Failures: {breaker.failure_count}")
```

## Configuration

### Environment Variables

```bash
# Enable persistence (default: false)
ENABLE_CIRCUIT_BREAKER_PERSISTENCE=true

# Redis configuration (already exists)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### Redis Key Structure

```
circuit_breaker:{name}:state
```

Example:
```
circuit_breaker:firecrawl:state -> {"state": "open", "failure_count": 5, "opened_at": 1698765432.0, "half_open_attempts": 0}
```

## Backward Compatibility

The implementation is **fully backward compatible**:

1. **Works without Redis**: If Redis is unavailable, circuit breaker uses in-memory state only
2. **Works without persistence flag**: If `ENABLE_CIRCUIT_BREAKER_PERSISTENCE=false`, no persistence is used
3. **No breaking changes**: Existing code continues to work without modification
4. **Optional parameter**: `persistence_backend` parameter is optional in `CircuitBreaker.__init__()`

## Performance Considerations

### Async and Non-Blocking

State persistence is **non-blocking**:
- Uses `asyncio.create_task()` for background syncing
- Doesn't wait for Redis write to complete
- Failures are logged but don't affect circuit breaker operation

### Redis Load

Minimal Redis usage:
- Only writes on state changes (not every request)
- Writes occur on:
  - Circuit opens (failure threshold reached)
  - Circuit closes (recovery success)
  - Circuit reset
  - Failure count changes
- Typical: 1-5 writes per circuit per minute (during failures)

### TTL-Based Cleanup

Redis keys auto-expire:
- OPEN circuits: 24 hours
- CLOSED circuits: 1 hour
- No manual cleanup required

## Future Enhancements

Potential improvements:
1. **Redis Cluster Support**: Handle distributed circuit breakers
2. **Metrics Integration**: Track persistence success/failure rates
3. **Admin API**: Endpoints to view/modify circuit breaker state
4. **Configurable TTLs**: Per-circuit TTL configuration
5. **State History**: Track circuit breaker state transitions over time

## Files Modified/Created

### New Files
- `/home/user/graphrag/apps/api/app/core/circuit_breaker_persistence.py` (138 lines)
- `/home/user/graphrag/apps/api/tests/integration/test_circuit_breaker_persistence.py` (152 lines)
- `/home/user/graphrag/apps/api/test_circuit_breaker_persistence.py` (117 lines, demo script)

### Modified Files
- `/home/user/graphrag/apps/api/app/core/resilience.py`:
  - Added persistence support to `CircuitBreaker` class
  - Added `load_from_backend()` and `sync_to_backend()` methods
  - Updated `get_circuit_breaker()` to accept `redis_client` parameter
  - Added automatic state loading in `execute()`

- `/home/user/graphrag/apps/api/app/core/config.py`:
  - Added `ENABLE_CIRCUIT_BREAKER_PERSISTENCE` flag
  - Updated config summary to include persistence flag

- `/home/user/graphrag/apps/api/tests/core/test_resilience.py`:
  - Added 5 new test cases for persistence
  - All 29 tests passing (100% success rate)

## Test Results

```bash
$ cd apps/api && uv run pytest tests/core/test_resilience.py -v

============================= test session starts ==============================
collected 29 items

tests/core/test_resilience.py::TestRetryPolicy::test_default_policy PASSED
tests/core/test_resilience.py::TestRetryPolicy::test_get_delay_exponential PASSED
tests/core/test_resilience.py::TestRetryPolicy::test_get_delay_respects_max PASSED
tests/core/test_resilience.py::TestRetryPolicy::test_get_delay_with_jitter PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_initial_state_closed PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_opens_after_threshold_failures PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_transitions_to_half_open_after_timeout PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_closes_on_success_in_half_open PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_reopens_on_failure_in_half_open PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_reset_closes_circuit PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_execute_with_success PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_execute_with_failure PASSED
tests/core/test_resilience.py::TestCircuitBreaker::test_execute_rejects_when_open PASSED
tests/core/test_resilience.py::TestRetryWithBackoff::test_succeeds_on_first_attempt PASSED
tests/core/test_resilience.py::TestRetryWithBackoff::test_retries_on_failure PASSED
tests/core/test_resilience.py::TestRetryWithBackoff::test_exhausts_retries_and_raises PASSED
tests/core/test_resilience.py::TestRetryWithBackoff::test_respects_circuit_breaker PASSED
tests/core/test_resilience.py::TestRetryWithBackoff::test_passes_args_and_kwargs PASSED
tests/core/test_resilience.py::TestWithRetryDecorator::test_decorator_applies_retry PASSED
tests/core/test_resilience.py::TestWithRetryDecorator::test_decorator_with_circuit_breaker PASSED
tests/core/test_resilience.py::TestPredefinedPolicies::test_network_retry_policy PASSED
tests/core/test_resilience.py::TestPredefinedPolicies::test_get_circuit_breaker_creates_new PASSED
tests/core/test_resilience.py::TestPredefinedPolicies::test_get_circuit_breaker_returns_existing PASSED
tests/core/test_resilience.py::TestPredefinedPolicies::test_reset_all_circuit_breakers PASSED
tests/core/test_resilience.py::TestCircuitBreakerPersistence::test_persistence_backend_save_and_load PASSED
tests/core/test_resilience.py::TestCircuitBreakerPersistence::test_circuit_breaker_with_persistence_loads_state PASSED
tests/core/test_resilience.py::TestCircuitBreakerPersistence::test_circuit_breaker_persists_state_changes PASSED
tests/core/test_resilience.py::TestCircuitBreakerPersistence::test_persistence_backend_handles_redis_errors_gracefully PASSED
tests/core/test_resilience.py::TestCircuitBreakerPersistence::test_circuit_breaker_works_without_persistence PASSED

======================== 29 passed, 2 warnings in 2.61s =========================
```

## Conclusion

Successfully implemented Redis-backed persistence for circuit breaker state following TDD principles:

✅ **RED**: Wrote failing tests first (5 new test cases)
✅ **GREEN**: Implemented features to make tests pass
✅ **REFACTOR**: Cleaned up code while keeping tests passing

The implementation:
- Is fully backward compatible
- Handles Redis unavailability gracefully
- Follows existing code patterns and conventions
- Has comprehensive test coverage (29 tests, 100% passing)
- Uses async/non-blocking I/O
- Includes proper error handling and logging
- Is production-ready (disabled by default, opt-in)
