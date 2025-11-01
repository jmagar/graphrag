/**
 * API Middleware Tests
 * 
 * Tests for rate limiting middleware
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { NextRequest, NextResponse } from 'next/server';
import { withRateLimit, getRateLimiter } from '@/lib/apiMiddleware';

// Mock NextRequest
function createMockRequest(options: {
  ip?: string;
  userAgent?: string;
  headers?: Record<string, string>;
} = {}): NextRequest {
  const headers = new Headers({
    'x-forwarded-for': options.ip || '127.0.0.1',
    'user-agent': options.userAgent || 'test-agent',
    ...options.headers,
  });

  return new NextRequest('http://localhost:3000/api/test', {
    headers,
  });
}

describe('API Middleware - Rate Limiting', () => {
  beforeEach(() => {
    // Reset rate limiters between tests
    vi.clearAllMocks();
  });

  it('should allow requests under the limit', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    // Make 3 requests (under limit)
    const request1 = createMockRequest({ ip: '192.168.1.1' });
    const request2 = createMockRequest({ ip: '192.168.1.1' });
    const request3 = createMockRequest({ ip: '192.168.1.1' });

    const response1 = await rateLimitedHandler(request1);
    const response2 = await rateLimitedHandler(request2);
    const response3 = await rateLimitedHandler(request3);

    expect(response1.status).toBe(200);
    expect(response2.status).toBe(200);
    expect(response3.status).toBe(200);
    expect(mockHandler).toHaveBeenCalledTimes(3);
  });

  it('should block requests over the limit with 429', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    // Make 6 requests (over limit of 5)
    const requests = Array(6).fill(null).map(() => 
      createMockRequest({ ip: '192.168.1.2' })
    );

    const responses = await Promise.all(
      requests.map(req => rateLimitedHandler(req))
    );

    // First 5 should succeed
    expect(responses.slice(0, 5).every(r => r.status === 200)).toBe(true);
    
    // 6th should be rate limited
    expect(responses[5].status).toBe(429);
  });

  it('should include rate limit headers in 429 response', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    // Fill up the quota
    const requests = Array(6).fill(null).map(() => 
      createMockRequest({ ip: '192.168.1.3' })
    );

    const responses = await Promise.all(
      requests.map(req => rateLimitedHandler(req))
    );

    const rateLimitedResponse = responses[5];
    
    expect(rateLimitedResponse.headers.get('Retry-After')).toBeTruthy();
    expect(rateLimitedResponse.headers.get('X-RateLimit-Limit')).toBe('10');
    expect(rateLimitedResponse.headers.get('X-RateLimit-Remaining')).toBe('0');
    expect(rateLimitedResponse.headers.get('X-RateLimit-Reset')).toBeTruthy();
  });

  it('should include error message in 429 response body', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    // Fill up the quota
    const requests = Array(6).fill(null).map(() => 
      createMockRequest({ ip: '192.168.1.4' })
    );

    const responses = await Promise.all(
      requests.map(req => rateLimitedHandler(req))
    );

    const rateLimitedResponse = responses[5];
    const body = await rateLimitedResponse.json();

    expect(body.error).toBe('Rate limit exceeded');
    expect(body.retryAfter).toBeGreaterThan(0);
    expect(body.message).toContain('Too many requests');
  });

  it('should track different IPs separately', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    // IP 1 fills quota
    const ip1Requests = Array(5).fill(null).map(() => 
      createMockRequest({ ip: '192.168.1.5' })
    );
    await Promise.all(ip1Requests.map(req => rateLimitedHandler(req)));

    // IP 2 should still be allowed
    const ip2Request = createMockRequest({ ip: '192.168.1.6' });
    const response = await rateLimitedHandler(ip2Request);

    expect(response.status).toBe(200);
  });

  it('should use x-forwarded-for header for IP', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    const request = createMockRequest({ 
      ip: '10.0.0.1, 192.168.1.7',
      headers: { 'x-forwarded-for': '10.0.0.1, 192.168.1.7' }
    });

    const response = await rateLimitedHandler(request);
    expect(response.status).toBe(200);
  });

  it('should handle missing IP gracefully', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    const headers = new Headers({
      'user-agent': 'test-agent',
    });

    const request = new NextRequest('http://localhost:3000/api/test', {
      headers,
    });

    const response = await rateLimitedHandler(request);
    expect(response.status).toBe(200);
  });

  it('should pass context to handler', async () => {
    const mockHandler = vi.fn().mockResolvedValue(
      NextResponse.json({ success: true })
    );

    const rateLimitedHandler = withRateLimit(
      getRateLimiter('message'),
      mockHandler
    );

    const request = createMockRequest({ ip: '192.168.1.8' });
    const context = { params: { id: '123' } };

    await rateLimitedHandler(request, context);

    expect(mockHandler).toHaveBeenCalledWith(request, context);
  });

  it('should get correct rate limiter for endpoint type', () => {
    const conversationLimiter = getRateLimiter('conversation');
    const messageLimiter = getRateLimiter('message');

    expect(conversationLimiter).toBeDefined();
    expect(messageLimiter).toBeDefined();
    expect(conversationLimiter).not.toBe(messageLimiter);
  });
});
