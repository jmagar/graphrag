/**
 * Rate Limiting Tests
 * 
 * Tests for RateLimiter, ClientRateLimiter, and CircuitBreaker
 */

import { RateLimiter, ClientRateLimiter, CircuitBreaker } from '@/lib/rateLimit';

describe('RateLimiter (Server-side)', () => {
  let rateLimiter: RateLimiter;

  beforeEach(() => {
    rateLimiter = new RateLimiter({
      maxRequests: 3,
      windowMs: 1000, // 1 second window for faster tests
    });
  });

  it('should allow requests under the limit', () => {
    const result1 = rateLimiter.check('client-1');
    const result2 = rateLimiter.check('client-1');
    const result3 = rateLimiter.check('client-1');

    expect(result1.allowed).toBe(true);
    expect(result2.allowed).toBe(true);
    expect(result3.allowed).toBe(true);
  });

  it('should block requests over the limit', () => {
    // Fill up the quota
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');

    // This should be blocked
    const result = rateLimiter.check('client-1');
    expect(result.allowed).toBe(false);
    expect(result.retryAfter).toBeGreaterThan(0);
  });

  it('should track different clients separately', () => {
    // Client 1 fills quota
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');

    // Client 2 should still be allowed
    const result = rateLimiter.check('client-2');
    expect(result.allowed).toBe(true);
  });

  it('should reset after the time window', async () => {
    // Fill quota
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');

    // Should be blocked
    expect(rateLimiter.check('client-1').allowed).toBe(false);

    // Wait for window to expire
    await new Promise(resolve => setTimeout(resolve, 1100));

    // Should be allowed again
    const result = rateLimiter.check('client-1');
    expect(result.allowed).toBe(true);
  });

  it('should allow manual reset', () => {
    // Fill quota
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');
    rateLimiter.check('client-1');

    // Should be blocked
    expect(rateLimiter.check('client-1').allowed).toBe(false);

    // Reset manually
    rateLimiter.reset('client-1');

    // Should be allowed again
    const result = rateLimiter.check('client-1');
    expect(result.allowed).toBe(true);
  });

  it('should use custom key generator', () => {
    const customRateLimiter = new RateLimiter({
      maxRequests: 2,
      windowMs: 1000,
      keyGenerator: (id) => `custom-${id}`,
    });

    customRateLimiter.check('test');
    customRateLimiter.check('test');
    
    const result = customRateLimiter.check('test');
    expect(result.allowed).toBe(false);
  });
});

describe('ClientRateLimiter (Client-side)', () => {
  let clientRateLimiter: ClientRateLimiter;
  const testKey = 'test-key';
  const maxRequests = 3;
  const windowMs = 1000;

  beforeEach(() => {
    clientRateLimiter = new ClientRateLimiter();
  });

  it('should allow requests under the limit', () => {
    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(true);
    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(true);
    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(true);
  });

  it('should block requests over the limit', () => {
    // Fill quota
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);

    // Should be blocked
    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(false);
  });

  it('should calculate retry after time', () => {
    // Fill quota
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);

    const retryAfter = clientRateLimiter.getRetryAfter(testKey, windowMs);
    expect(retryAfter).toBeGreaterThan(0);
    expect(retryAfter).toBeLessThanOrEqual(1);
  });

  it('should reset quota after time window', async () => {
    // Fill quota
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);

    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(false);

    // Wait for window to expire
    await new Promise(resolve => setTimeout(resolve, 1100));

    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(true);
  });

  it('should deduplicate requests with same key', async () => {
    const mockFn = jest.fn().mockResolvedValue('result');

    // Make two requests with same key simultaneously
    const promise1 = clientRateLimiter.deduplicate('key-1', mockFn);
    const promise2 = clientRateLimiter.deduplicate('key-1', mockFn);

    const [result1, result2] = await Promise.all([promise1, promise2]);

    // Both should resolve to same result
    expect(result1).toBe('result');
    expect(result2).toBe('result');
    
    // But function should only be called once
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('should not deduplicate requests with different keys', async () => {
    const mockFn = jest.fn().mockResolvedValue('result');

    // Make two requests with different keys
    const promise1 = clientRateLimiter.deduplicate('key-1', mockFn);
    const promise2 = clientRateLimiter.deduplicate('key-2', mockFn);

    await Promise.all([promise1, promise2]);

    // Function should be called twice
    expect(mockFn).toHaveBeenCalledTimes(2);
  });

  it('should allow manual reset', () => {
    // Fill quota
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);
    clientRateLimiter.isAllowed(testKey, maxRequests, windowMs);

    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(false);

    clientRateLimiter.reset();

    expect(clientRateLimiter.isAllowed(testKey, maxRequests, windowMs)).toBe(true);
  });
});

describe('CircuitBreaker', () => {
  let circuitBreaker: CircuitBreaker;

  beforeEach(() => {
    circuitBreaker = new CircuitBreaker(3, 1000); // 3 failures, 1 second reset
  });

  it('should start in closed state', () => {
    expect(circuitBreaker.getState()).toBe('closed');
  });

  it('should execute successful requests', async () => {
    const mockFn = jest.fn().mockResolvedValue('success');
    const result = await circuitBreaker.execute(mockFn);

    expect(result).toBe('success');
    expect(mockFn).toHaveBeenCalledTimes(1);
    expect(circuitBreaker.getState()).toBe('closed');
  });

  it('should open after threshold failures', async () => {
    const mockFn = jest.fn().mockRejectedValue(new Error('failure'));

    // Trigger failures
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow('failure');
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow('failure');
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow('failure');

    // Circuit should be open now
    expect(circuitBreaker.getState()).toBe('open');

    // Further requests should fail immediately
    await expect(
      circuitBreaker.execute(jest.fn().mockResolvedValue('never called'))
    ).rejects.toThrow('Circuit breaker is open');
  });

  it('should transition to half-open after timeout', async () => {
    const mockFn = jest.fn().mockRejectedValue(new Error('failure'));

    // Open the circuit
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow();

    expect(circuitBreaker.getState()).toBe('open');

    // Wait for reset timeout
    await new Promise(resolve => setTimeout(resolve, 1100));

    // Next request should attempt (half-open)
    const successFn = jest.fn().mockResolvedValue('success');
    await circuitBreaker.execute(successFn);

    // Should transition back to closed
    expect(circuitBreaker.getState()).toBe('closed');
  });

  it('should reset to closed on successful half-open request', async () => {
    const failFn = jest.fn().mockRejectedValue(new Error('failure'));
    const successFn = jest.fn().mockResolvedValue('success');

    // Open the circuit
    await expect(circuitBreaker.execute(failFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(failFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(failFn)).rejects.toThrow();

    // Wait for reset
    await new Promise(resolve => setTimeout(resolve, 1100));

    // Successful request should close circuit
    await circuitBreaker.execute(successFn);
    expect(circuitBreaker.getState()).toBe('closed');

    // Further requests should work normally
    await circuitBreaker.execute(successFn);
    expect(successFn).toHaveBeenCalledTimes(2);
  });

  it('should allow manual reset', async () => {
    const mockFn = jest.fn().mockRejectedValue(new Error('failure'));

    // Open the circuit
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(mockFn)).rejects.toThrow();

    expect(circuitBreaker.getState()).toBe('open');

    // Manual reset
    circuitBreaker.reset();

    expect(circuitBreaker.getState()).toBe('closed');
  });

  it('should not increment failures on successful requests', async () => {
    const successFn = jest.fn().mockResolvedValue('success');
    const failFn = jest.fn().mockRejectedValue(new Error('failure'));

    // Successful request
    await circuitBreaker.execute(successFn);
    
    // Two failures (not enough to open)
    await expect(circuitBreaker.execute(failFn)).rejects.toThrow();
    await expect(circuitBreaker.execute(failFn)).rejects.toThrow();

    // Another success
    await circuitBreaker.execute(successFn);

    // Circuit should still be closed (successes don't increment)
    expect(circuitBreaker.getState()).toBe('closed');
  });
});
