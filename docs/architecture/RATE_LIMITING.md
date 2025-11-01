# Rate Limiting Architecture

**Last Updated:** 2025-11-01  
**Status:** Production Ready  

## Overview

GraphRAG implements a **multi-layer rate limiting strategy** to protect against abuse while maintaining a smooth user experience. This document explains the architecture, configuration, and troubleshooting of our rate limiting system.

### Why Multi-Layer Rate Limiting?

We use both **client-side** and **server-side** rate limiting for defense in depth:

1. **Client-Side (Proactive)** - Provides immediate feedback to users and reduces unnecessary network calls
2. **Server-Side (Enforcement)** - Final protection layer that works even if client is bypassed

This approach:
- ✅ Improves UX with instant feedback
- ✅ Reduces server load from redundant requests
- ✅ Protects against direct API access
- ✅ Allows different limits for different endpoints

---

## Architecture

### Layer 1: Client-Side Rate Limiting

**Location:** `apps/web/lib/rateLimit.ts`, `apps/web/hooks/useConversationSave.ts`

**Purpose:** Proactive user protection and UX optimization

**Implementation:**
```typescript
// Sliding window algorithm per client IP/session
class ClientRateLimiter {
  private requests: Map<string, number[]> = new Map();
  
  isAllowed(key: string, maxRequests: number, windowMs: number): boolean {
    // Track requests in sliding time window
    // Return false if limit exceeded
  }
}
```

**Key Characteristics:**
- Uses sliding window algorithm (more accurate than fixed window)
- Tracked per user session/IP
- Provides immediate feedback (no server round-trip)
- More restrictive than server limits

### Layer 2: Server-Side Rate Limiting

**Location:** `apps/web/lib/apiMiddleware.ts`

**Purpose:** Final enforcement and protection against API abuse

**Implementation:**
```typescript
// Header-based tracking with Redis backend (future)
export function rateLimit(
  req: NextRequest,
  identifier: string,
  maxRequests: number,
  windowMs: number
): boolean {
  // Track via headers or Redis
  // Enforce stricter limits than client
}
```

**Key Characteristics:**
- Tracked by IP address or API key
- Uses `X-RateLimit-*` headers for visibility
- Can leverage Redis for multi-instance deployments
- Less restrictive than client (allows legitimate bursts)

---

## Configuration

### Current Rate Limits

All limits defined in `apps/web/lib/rateLimit.ts`:

```typescript
export const RATE_LIMIT_CONFIG = {
  // Client-side limits (proactive)
  CLIENT_CONVERSATION_SAVE: {
    maxRequests: 3,
    windowMs: 10000, // 10 seconds
    rationale: "Prevents rapid-fire saves during UI interactions"
  },
  
  // Server-side limits (enforcement)
  SERVER_CONVERSATION_CREATE: {
    maxRequests: 10,
    windowMs: 60000, // 1 minute
    rationale: "Protects against conversation spam"
  },
  SERVER_MESSAGE_SAVE: {
    maxRequests: 5,
    windowMs: 10000, // 10 seconds
    rationale: "Protects against message spam while allowing legitimate bursts"
  }
} as const;
```

### Why Client Limits Are MORE Restrictive

**Client:** 3 saves / 10 seconds = 0.3 req/sec  
**Server:** 5 saves / 10 seconds = 0.5 req/sec

**Rationale:**
- Client limit catches accidental rapid clicks
- Server limit allows some burst for legitimate use cases
- If client is bypassed, server still protects
- Different contexts have different needs

### Adjusting Limits

To modify limits, edit `RATE_LIMIT_CONFIG` in `apps/web/lib/rateLimit.ts`:

```typescript
// Example: Increase conversation creation limit
SERVER_CONVERSATION_CREATE: {
  maxRequests: 20,  // Was 10
  windowMs: 60000,
  rationale: "Allow more concurrent users during peak hours"
}
```

**Testing After Changes:**
```bash
npm run test -- rateLimit.test.ts
```

---

## Implementation Details

### Sliding Window Algorithm

Our rate limiting uses a **sliding window** approach for accuracy:

```typescript
// Fixed window (less accurate)
// |----window 1----|----window 2----|
//      5 reqs           5 reqs       ✓ allowed (10 total across 2 windows)

// Sliding window (more accurate)
// |----window----|
//        ^now
//      5 old + 6 new = 11 reqs ✗ rejected (exceeds 10)
```

**Benefits:**
- Prevents burst at window boundaries
- More consistent rate enforcement
- Fairer to all users

### Client-Side Implementation

**File:** `apps/web/hooks/useConversationSave.ts`

```typescript
const saveConversation = useCallback(async (data: ConversationData) => {
  // Check rate limit BEFORE making request
  if (!rateLimiter.isAllowed('conversation-save', 3, 10000)) {
    toast.error('Too many save attempts. Please wait a moment.');
    return;
  }
  
  // Proceed with save
  await fetch('/api/conversations', { method: 'POST', body: data });
}, []);
```

**Key Points:**
- Checks limit BEFORE network call
- Shows user-friendly error message
- Prevents wasted bandwidth

### Server-Side Implementation

**File:** `apps/web/lib/apiMiddleware.ts`

```typescript
export async function POST(req: NextRequest) {
  const identifier = req.ip || req.headers.get('x-forwarded-for') || 'unknown';
  
  if (!rateLimit(identifier, 5, 10000)) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      {
        status: 429,
        headers: {
          'X-RateLimit-Limit': '5',
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': String(Date.now() + 10000),
          'Retry-After': '10'
        }
      }
    );
  }
  
  // Process request
}
```

**Response Headers:**
- `X-RateLimit-Limit` - Maximum requests allowed
- `X-RateLimit-Remaining` - Requests remaining in window
- `X-RateLimit-Reset` - Unix timestamp when limit resets
- `Retry-After` - Seconds until retry allowed

### Circuit Breaker Pattern

**File:** `apps/web/lib/rateLimit.ts`

```typescript
class CircuitBreaker {
  // States: CLOSED (normal) -> OPEN (blocked) -> HALF_OPEN (testing)
  
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      throw new Error('Circuit breaker is OPEN');
    }
    // Execute and track failures
  }
}
```

**Use Cases:**
- Protect against cascading failures
- Automatic recovery from service issues
- Prevents retry storms

---

## Monitoring

### Client-Side Metrics

Track in browser console (development mode):

```typescript
// Log rate limit events
logger.debug('Rate limit hit', {
  endpoint: '/api/conversations',
  limit: 3,
  window: '10s',
  remaining: 0
});
```

### Server-Side Metrics

Monitor via response headers:

```bash
curl -I https://your-app.com/api/messages
# X-RateLimit-Limit: 5
# X-RateLimit-Remaining: 3
# X-RateLimit-Reset: 1698765432
```

### Recommended Monitoring

**Metrics to Track:**
- Rate limit rejections per endpoint
- 429 status code frequency
- Average requests per user session
- Peak request rates by time of day

**Alerts to Configure:**
- Spike in 429 responses (possible attack)
- Unusual rate limit pattern (bot activity)
- Rate limit bypass attempts

---

## Troubleshooting

### Issue: "Too many save attempts" error

**Symptoms:** User sees error message when saving conversation

**Cause:** Client-side rate limit (3 saves / 10 seconds) exceeded

**Solutions:**
1. **User Action:** Wait 10 seconds before retrying
2. **Developer:** Check for accidental double-click bugs
3. **Config:** Increase limit if legitimate use case

### Issue: 429 Too Many Requests

**Symptoms:** Server returns 429 status code

**Cause:** Server-side rate limit (5 saves / 10 seconds) exceeded

**Solutions:**
1. **Check:** Is client-side limit being bypassed?
2. **Investigate:** Unusual traffic patterns or bot activity
3. **Review:** Logs for repeated requests from same IP
4. **Adjust:** Limits if legitimate high-volume user

### Issue: Rate limits not working

**Symptoms:** Users can make unlimited requests

**Checklist:**
- ✅ Check `rateLimit.ts` is imported correctly
- ✅ Verify `isAllowed()` is called BEFORE request
- ✅ Confirm middleware is applied to route
- ✅ Check for caching issues (stale rate limiter instance)

**Debug:**
```typescript
console.log('Rate limiter state:', {
  requests: rateLimiter.requests,
  isAllowed: rateLimiter.isAllowed('key', 3, 10000)
});
```

### Issue: Legitimate users blocked

**Symptoms:** Power users hitting limits during normal use

**Analysis:**
1. Review actual usage patterns in logs
2. Calculate expected request rate for user workflow
3. Compare against current limits

**Solutions:**
- Increase limits if usage is legitimate
- Implement tiered limits (free vs. premium users)
- Add per-user customization for known power users

---

## Best Practices

### 1. Always Layer Your Limits

✅ **Good:**
```typescript
// Client checks first (3/10s)
if (!clientRateLimiter.isAllowed()) return;

// Server enforces (5/10s)
if (!serverRateLimiter.isAllowed()) return 429;
```

❌ **Bad:**
```typescript
// Only server-side - wastes bandwidth
if (!serverRateLimiter.isAllowed()) return 429;
```

### 2. Make Client Limits MORE Restrictive

```typescript
// Client: 3 requests / 10 seconds (stricter)
// Server: 5 requests / 10 seconds (lenient)
```

**Why:** Catches user errors immediately while allowing server flexibility

### 3. Use Descriptive Error Messages

✅ **Good:**
```typescript
toast.error('Please wait 10 seconds before saving again. Your work is safe!');
```

❌ **Bad:**
```typescript
alert('Error 429');
```

### 4. Provide Retry Information

```typescript
return new Response(JSON.stringify({ error: 'Rate limit exceeded' }), {
  status: 429,
  headers: {
    'Retry-After': '10',  // Tells client when to retry
    'X-RateLimit-Reset': String(resetTime)
  }
});
```

### 5. Log Rate Limit Events

```typescript
logger.warn('Rate limit exceeded', {
  ip: req.ip,
  endpoint: req.url,
  limit: '5/10s',
  timestamp: Date.now()
});
```

**Use for:**
- Detecting abuse patterns
- Capacity planning
- Adjusting limits based on real usage

---

## Future Enhancements

### 1. Redis-Based Rate Limiting

**Current:** In-memory (single instance)  
**Future:** Redis-based (multi-instance)

```typescript
import Redis from 'ioredis';

class RedisRateLimiter {
  async isAllowed(key: string, max: number, window: number): Promise<boolean> {
    const count = await redis.incr(`ratelimit:${key}`);
    if (count === 1) {
      await redis.expire(`ratelimit:${key}`, window / 1000);
    }
    return count <= max;
  }
}
```

**Benefits:**
- Shared state across instances
- Persistent limits during deploys
- More accurate enforcement

### 2. Tiered Rate Limits

```typescript
const TIER_LIMITS = {
  free: { maxRequests: 3, windowMs: 10000 },
  pro: { maxRequests: 10, windowMs: 10000 },
  enterprise: { maxRequests: 100, windowMs: 10000 }
};
```

### 3. Adaptive Rate Limiting

```typescript
// Adjust limits based on server load
const currentLoad = getServerLoad();
const adjustedLimit = BASE_LIMIT * (1 - currentLoad * 0.5);
```

### 4. Rate Limit Analytics Dashboard

Track and visualize:
- Requests per endpoint over time
- Rate limit hit frequency
- Top rate-limited IPs/users
- Optimal limit recommendations

---

## Testing

### Unit Tests

**File:** `apps/web/__tests__/lib/rateLimit.test.ts`

```typescript
describe('RateLimiter', () => {
  test('allows requests within limit', () => {
    const limiter = new RateLimiter();
    expect(limiter.isAllowed('test', 3, 10000)).toBe(true);
    expect(limiter.isAllowed('test', 3, 10000)).toBe(true);
    expect(limiter.isAllowed('test', 3, 10000)).toBe(true);
  });
  
  test('blocks requests exceeding limit', () => {
    const limiter = new RateLimiter();
    for (let i = 0; i < 3; i++) {
      limiter.isAllowed('test', 3, 10000);
    }
    expect(limiter.isAllowed('test', 3, 10000)).toBe(false);
  });
});
```

### Integration Tests

```typescript
test('client limits more restrictive than server', () => {
  const clientLimit = RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.maxRequests;
  const serverLimit = RATE_LIMIT_CONFIG.SERVER_MESSAGE_SAVE.maxRequests;
  
  expect(clientLimit).toBeLessThan(serverLimit);
});
```

### Load Testing

```bash
# Test rate limiting under load
npm run test:load

# Simulate 100 concurrent users
for i in {1..100}; do
  curl -X POST http://localhost:4300/api/conversations &
done
```

---

## Summary

### Quick Reference

| Layer | Limit | Window | Purpose |
|-------|-------|--------|---------|
| Client (Conversation Save) | 3 | 10s | Prevent accidental spam |
| Server (Conversation Create) | 10 | 60s | Protect against abuse |
| Server (Message Save) | 5 | 10s | Balance protection & UX |

### Key Takeaways

1. ✅ **Multi-layer defense** - Client + Server protection
2. ✅ **Client limits stricter** - Better UX, less server load
3. ✅ **Sliding window** - More accurate than fixed window
4. ✅ **Clear errors** - User-friendly messages with retry info
5. ✅ **Monitor & adjust** - Track metrics and tune limits

### Related Documentation

- [API Middleware](./API_MIDDLEWARE.md) - Server-side implementation details
- [Frontend Architecture](./FRONTEND.md) - Client-side hooks and patterns
- [Deployment Guide](../deployment/README.md) - Production rate limiting setup

---

**Questions or Issues?**  
- Check troubleshooting section above
- Review test files for usage examples  
- File an issue in the repository
