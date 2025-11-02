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

const claudeChatRateLimiter = new RateLimiter({
  maxRequests: 10, // Max 10 Claude API calls
  windowMs: 60000, // Per minute
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
 * Supports both handlers with and without context parameters
 */
export function withRateLimit<T extends Response | NextResponse, C = unknown>(
  limiter: RateLimiter,
  handler: (request: NextRequest, context: C) => Promise<T>
): (request: NextRequest, context: C) => Promise<NextResponse | T>;

export function withRateLimit<T extends Response | NextResponse>(
  limiter: RateLimiter,
  handler: (request: NextRequest) => Promise<T>
): (request: NextRequest) => Promise<NextResponse | T>;

export function withRateLimit<T extends Response | NextResponse, C = unknown>(
  limiter: RateLimiter,
  handler: (request: NextRequest, context?: C) => Promise<T>
) {
  return async (request: NextRequest, context?: C): Promise<NextResponse | T> => {
    const clientId = getClientId(request);
    const { allowed, retryAfter } = limiter.check(clientId);

    if (!allowed) {
      console.warn(`Rate limit exceeded for client: ${clientId}`);
      const retryAfterSeconds = retryAfter || 60; // Default to 60 seconds if undefined
      return NextResponse.json(
        { 
          error: 'Rate limit exceeded',
          retryAfter: retryAfterSeconds,
          message: `Too many requests. Please try again in ${retryAfterSeconds} seconds.`
        },
        { 
          status: 429,
          headers: {
            'Retry-After': String(retryAfterSeconds),
            'X-RateLimit-Limit': '10',
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': String(Date.now() + (retryAfterSeconds * 1000))
          }
        }
      );
    }

    return handler(request, context as C);
  };
}

/**
 * Get appropriate rate limiter for endpoint
 */
export function getRateLimiter(endpoint: 'conversation' | 'message' | 'claude-chat'): RateLimiter {
  switch (endpoint) {
    case 'conversation':
      return conversationRateLimiter;
    case 'message':
      return messageRateLimiter;
    case 'claude-chat':
      return claudeChatRateLimiter;
    default:
      return conversationRateLimiter;
  }
}
