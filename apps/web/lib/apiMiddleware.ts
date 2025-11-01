/**
 * API Middleware - Rate limiting and protection for API routes
 */

import { NextRequest, NextResponse } from 'next/server';
import { RateLimiter } from './rateLimit';

// Rate limiters for different endpoint types
const conversationRateLimiter = new RateLimiter({
  maxRequests: 10, // Max 10 requests
  windowMs: 60000, // Per minute
});

const messageRateLimiter = new RateLimiter({
  maxRequests: 5, // Max 5 message saves
  windowMs: 10000, // Per 10 seconds
});

/**
 * Get client identifier from request
 */
function getClientId(request: NextRequest): string {
  // Try to get IP from headers (works with proxies)
  const forwarded = request.headers.get('x-forwarded-for');
  const ip = forwarded?.split(',')[0] || 
             request.headers.get('x-real-ip') ||
             'unknown';
  
  // Include user agent for better uniqueness
  const userAgent = request.headers.get('user-agent') || 'unknown';
  
  return `${ip}-${userAgent.substring(0, 50)}`;
}

/**
 * Apply rate limiting to a request
 */
export function withRateLimit(
  limiter: RateLimiter,
  handler: (request: NextRequest, context?: unknown) => Promise<NextResponse>
) {
  return async (request: NextRequest, context?: unknown): Promise<NextResponse> => {
    const clientId = getClientId(request);
    const { allowed, retryAfter } = limiter.check(clientId);

    if (!allowed) {
      console.warn(`Rate limit exceeded for client: ${clientId}`);
      return NextResponse.json(
        { 
          error: 'Rate limit exceeded',
          retryAfter,
          message: `Too many requests. Please try again in ${retryAfter} seconds.`
        },
        { 
          status: 429,
          headers: {
            'Retry-After': String(retryAfter),
            'X-RateLimit-Limit': '10',
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': String(Date.now() + (retryAfter * 1000))
          }
        }
      );
    }

    return handler(request, context);
  };
}

/**
 * Get appropriate rate limiter for endpoint
 */
export function getRateLimiter(endpoint: 'conversation' | 'message'): RateLimiter {
  switch (endpoint) {
    case 'conversation':
      return conversationRateLimiter;
    case 'message':
      return messageRateLimiter;
    default:
      return conversationRateLimiter;
  }
}
