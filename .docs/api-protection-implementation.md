# API Protection Implementation

## Problem

The previous fix for the React render cycle warning caused a critical issue:
- **API Spam**: The useEffect hook was triggering on every message update, causing hundreds of duplicate save requests
- **No Rate Limiting**: No protection against rapid-fire API calls
- **No Deduplication**: Same message being saved multiple times
- **No Circuit Breaker**: No protection against cascading failures

## Solution

Implemented a comprehensive multi-layer protection system:

### 1. Rate Limiting (`/lib/rateLimit.ts`)

**Server-Side Rate Limiter**:
```typescript
const messageRateLimiter = new RateLimiter({
  maxRequests: 5,      // Max 5 requests
  windowMs: 10000,     // Per 10 seconds
});
```

**Client-Side Rate Limiter**:
```typescript
const rateLimiter = new ClientRateLimiter({
  maxRequests: 3,      // Max 3 save operations  
  windowMs: 10000,     // Per 10 seconds
});
```

### 2. API Middleware (`/lib/apiMiddleware.ts`)

Wraps API routes with rate limiting:
```typescript
export const POST = withRateLimit(
  getRateLimiter('message'),
  handlePOST
);
```

Returns 429 (Too Many Requests) with:
- `Retry-After` header
- Rate limit information
- Clear error message

### 3. Circuit Breaker

Prevents cascading failures:
```typescript
const circuitBreaker = new CircuitBreaker(
  5,      // Open after 5 failures
  60000   // Reset after 60 seconds
);
```

**States**:
- **Closed**: Normal operation
- **Open**: Too many failures - rejects requests immediately
- **Half-Open**: Testing recovery

### 4. Request Deduplication

Prevents duplicate requests:
```typescript
// Generate hash from content
const hash = generateHash(userMessage, assistantMessage);

// Skip if duplicate
if (hash === lastSaveHashRef.current) {
  return { success: false, reason: 'duplicate' };
}

// Deduplicate parallel requests
await rateLimiter.deduplicate(saveKey, async () => {
  // Save logic
});
```

### 5. Safe Save Hook (`/hooks/useConversationSave.ts`)

Provides a safe API for saving conversations:

```typescript
const { saveMessages, canSave, circuitState } = useConversationSave();

// All safety checks built-in:
// - Rate limiting
// - Deduplication  
// - Circuit breaker
// - In-progress checks
```

### 6. Queue-Based Saving

Uses `queueMicrotask` to ensure saves happen AFTER render:

```typescript
const queueSave = (userMessage: string, assistantMessage: string) => {
  queueMicrotask(() => {
    saveMessages({
      userMessage,
      assistantMessage,
      conversationId: currentConversation?.id
    }).catch(error => {
      console.error('Background save failed:', error);
    });
  });
};
```

## Protection Layers

1. **Client-Side**:
   - Rate limiting (3 requests / 10s)
   - Request deduplication
   - In-progress check
   - Circuit breaker

2. **Server-Side**:
   - Rate limiting (5 requests / 10s)
   - Client identification (IP + User Agent)
   - Timeout protection (30s)

3. **Queue Management**:
   - `queueMicrotask` for post-render execution
   - Non-blocking async operations
   - Graceful error handling

## Benefits

✅ **No API Spam**: Maximum 3 saves per 10 seconds client-side  
✅ **Duplicate Prevention**: Hash-based deduplication  
✅ **Failure Protection**: Circuit breaker stops cascading failures  
✅ **React Compliant**: No state updates during render  
✅ **User Friendly**: Clear error messages with retry info  
✅ **Production Ready**: Robust error handling and logging

## Usage

```typescript
// In components
import { useConversationSave } from '@/hooks/useConversationSave';

const { saveMessages, canSave } = useConversationSave();

// Check if save is allowed
if (canSave) {
  await saveMessages({
    userMessage: 'Hello',
    assistantMessage: 'Hi there!',
    conversationId: '123'
  });
}
```

## Testing

To test the protection:
```bash
# Should see rate limiting kick in after 3 rapid saves
# Should see deduplication preventing duplicate content
# Should see circuit breaker open after repeated failures
```

## Future Improvements

1. **Persistent Circuit Breaker**: Store state in Redis/database
2. **Per-User Rate Limiting**: Track by authenticated user ID
3. **Adaptive Rate Limiting**: Adjust limits based on load
4. **Metrics & Monitoring**: Track rate limit hits, circuit breaker states
5. **Distributed Rate Limiting**: Use Redis for multi-instance deployments
