#!/usr/bin/env python
"""
Demonstration script for circuit breaker persistence.

This script simulates application restarts to show that circuit breaker state
persists across restarts when Redis backend is enabled.

Usage:
    # Enable persistence in .env:
    # ENABLE_CIRCUIT_BREAKER_PERSISTENCE=true

    # First run - open the circuit
    python test_circuit_breaker_persistence.py open

    # Second run - verify state persisted
    python test_circuit_breaker_persistence.py check

    # Third run - reset the circuit
    python test_circuit_breaker_persistence.py reset
"""

import asyncio
import sys
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    get_circuit_breaker,
)
from app.core.config import settings
from app.services.redis_service import RedisService


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    # Initialize Redis service
    redis_service = RedisService()
    redis_available = await redis_service.is_available()

    if not redis_available:
        print("❌ Redis is not available. Cannot test persistence.")
        sys.exit(1)

    if not settings.ENABLE_CIRCUIT_BREAKER_PERSISTENCE:
        print("⚠️ ENABLE_CIRCUIT_BREAKER_PERSISTENCE is False. State will not persist.")
        print("   Set ENABLE_CIRCUIT_BREAKER_PERSISTENCE=true in .env to enable.")

    print(f"\n{'='*60}")
    print(f"Circuit Breaker Persistence Test - Command: {command}")
    print(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"Persistence Enabled: {settings.ENABLE_CIRCUIT_BREAKER_PERSISTENCE}")
    print(f"{'='*60}\n")

    # Get or create circuit breaker with persistence
    breaker = get_circuit_breaker(
        "test_service",
        config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60),
        redis_client=redis_service.client if redis_available else None,
    )

    # Load state from backend
    if breaker.persistence_backend:
        await breaker.load_from_backend()

    if command == "open":
        print("📊 Current state BEFORE opening:")
        print(f"   State: {breaker.state.value}")
        print(f"   Failure count: {breaker.failure_count}")
        print()

        # Simulate failures to open circuit
        print("🔨 Simulating failures to open circuit...")
        for i in range(3):
            breaker.record_failure()
            print(f"   Failure {i + 1} recorded")

        # Wait for background persistence tasks
        await asyncio.sleep(0.2)

        print()
        print("📊 Current state AFTER opening:")
        print(f"   State: {breaker.state.value}")
        print(f"   Failure count: {breaker.failure_count}")
        print()
        print("✅ Circuit breaker is now OPEN")
        print("🔄 Run 'python test_circuit_breaker_persistence.py check' to verify persistence")

    elif command == "check":
        print("📊 Circuit breaker state (loaded from Redis):")
        print(f"   State: {breaker.state.value}")
        print(f"   Failure count: {breaker.failure_count}")
        print()

        if breaker.state.value == "open":
            print("✅ SUCCESS! Circuit breaker state persisted across 'restart'")
            print("   The circuit is still OPEN, as expected.")
        else:
            print("❌ State did not persist. Circuit should be OPEN.")

    elif command == "reset":
        print("📊 Current state BEFORE reset:")
        print(f"   State: {breaker.state.value}")
        print(f"   Failure count: {breaker.failure_count}")
        print()

        print("🔄 Resetting circuit breaker...")
        breaker.reset()

        # Wait for background persistence tasks
        await asyncio.sleep(0.2)

        print()
        print("📊 Current state AFTER reset:")
        print(f"   State: {breaker.state.value}")
        print(f"   Failure count: {breaker.failure_count}")
        print()
        print("✅ Circuit breaker reset to CLOSED")

    else:
        print(f"❌ Unknown command: {command}")
        print("   Valid commands: open, check, reset")
        sys.exit(1)

    # Cleanup
    await redis_service.close()
    print()


if __name__ == "__main__":
    asyncio.run(main())
