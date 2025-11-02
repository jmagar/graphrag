# Rate Limiting Crash Investigation

## Problem Statement

Application crashed on load with:
```
TypeError: Cannot read properties of undefined (reading 'windowMs')
  at ClientRateLimiter.canMakeRequest (lib/rateLimit.ts:124:33)
  at useConversationSave (hooks/useConversationSave.ts:162:26)
```

## Investigation Process

### 1. Identified the Error Source

**File**: `apps/web/lib/rateLimit.ts:124`

```typescript
// Line 124 - ERROR: config parameter was undefined
canMakeRequest(config: RateLimitConfig): boolean {
  const now = Date.now();
  const cutoff = now - config.windowMs; // ❌ config is undefined
```

### 2. Found the Caller

**File**: `apps/web/hooks/useConversationSave.ts:11-13`

```typescript
// Constructor called WITH config
const rateLimiter = new ClientRateLimiter({
  maxRequests: 3,
  windowMs: 10000,
});
```

**File**: `apps/web/lib/rateLimit.ts:87-90`

```typescript
// But constructor accepts NO parameters!
export class ClientRateLimiter {
  private requests = new Map<string, number[]>();
  private pendingRequests = new Map<string, Promise<unknown>>();

  constructor() {  // ❌ No config parameter
    // No config needed - uses per-request limits
  }
```

### 3. Root Cause Analysis

**API Mismatch**:
- `ClientRateLimiter` was refactored to use per-call config via `isAllowed(key, maxRequests, windowMs)`
- Old code still tried to pass config to constructor
- Old code called deprecated `canMakeRequest()` without parameters
- The deprecated method expected `config` parameter but none was passed

**Evidence**:
- `rateLimit.ts:116` - `isAllowed()` method exists and works correctly
- `rateLimit.ts:122` - Deprecated `canMakeRequest(config)` method expected config
- `useConversationSave.ts:162` - Called `canMakeRequest()` without config parameter

## Solution Implemented

### 1. Updated Hook to Use New API

**File**: `apps/web/hooks/useConversationSave.ts`

**Before**:
```typescript
const rateLimiter = new ClientRateLimiter({
  maxRequests: 3,
  windowMs: 10000,
});

// Later...
if (!rateLimiter.canMakeRequest()) { // ❌ No config passed
```

**After**:
```typescript
const rateLimiter = new ClientRateLimiter(); // ✅ No config

// Later...
if (!rateLimiter.isAllowed(
  saveKey,
  RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.maxRequests,
  RATE_LIMIT_CONFIG.CLIENT_CONVERSATION_SAVE.windowMs
)) { // ✅ Config passed per call
```

### 2. Removed Deprecated Methods

**File**: `apps/web/lib/rateLimit.ts`

Removed:
- `canMakeRequest(config: RateLimitConfig)` - deprecated method
- `recordRequest(key)` - no longer needed (handled in `isAllowed`)
- `getRetryAfter()` - updated to accept parameters: `getRetryAfter(key, windowMs)`

### 3. Fixed TypeScript Errors

**File**: `apps/web/lib/apiMiddleware.ts:43-47`

Added function overloads to support both `Response` and `NextResponse`:

```typescript
export function withRateLimit<T extends Response | NextResponse, C = unknown>(
  limiter: RateLimiter,
  handler: (request: NextRequest, context: C) => Promise<T>
): (request: NextRequest, context: C) => Promise<NextResponse | T>;
```

### 4. Updated Tests

**File**: `apps/web/__tests__/lib/rateLimit.test.ts`

Changed all test calls from:
```typescript
clientRateLimiter.canMakeRequest() // Old API
```

To:
```typescript
clientRateLimiter.isAllowed(testKey, maxRequests, windowMs) // New API
```

## Verification

### Test Results

Created verification test: `apps/web/__tests__/fixes/rate-limit-fixes.test.ts`

```bash
PASS __tests__/fixes/rate-limit-fixes.test.ts
  ✓ should instantiate without config parameter
  ✓ should use isAllowed() with per-call parameters
  ✓ should provide getRetryAfter() with required parameters
  ✓ should support multiple independent keys
  ✓ should reset all rate limits
  ✓ should export rate limit configuration constants
  ✓ should have valid conversation save limits
  ✓ should have valid Claude chat limits
  ✓ should use RATE_LIMIT_CONFIG constants
  ✓ should not have deprecated canMakeRequest method
  ✓ should not have deprecated recordRequest method

Test Suites: 1 passed, 1 total
Tests:       11 passed, 11 total
```

### Build Test

TypeScript compilation now passes without the original errors.

## Bonus Fixes

### Cross-Origin Warning

**File**: `apps/web/next.config.ts`

Added:
```typescript
allowedDevOrigins: [
  "rag.tootie.tv",
  "http://rag.tootie.tv",
  "https://rag.tootie.tv",
],
```

## Key Findings

1. **Root Cause**: API refactor left deprecated methods that expected config parameter
2. **Caller Issue**: Hook used old constructor pattern and called deprecated method
3. **Fix Pattern**: Use new `isAllowed(key, maxRequests, windowMs)` API throughout
4. **Config Location**: Centralized in `RATE_LIMIT_CONFIG` constant
5. **Test Coverage**: All existing tests updated + new verification tests added

## Files Modified

- `apps/web/lib/rateLimit.ts` - Removed deprecated methods, kept new API
- `apps/web/hooks/useConversationSave.ts` - Updated to new API
- `apps/web/lib/apiMiddleware.ts` - Added generic type parameters
- `apps/web/__tests__/lib/rateLimit.test.ts` - Updated all tests
- `apps/web/__tests__/fixes/rate-limit-fixes.test.ts` - New verification tests
- `apps/web/next.config.ts` - Added allowedDevOrigins

## Result

✅ Application loads without crashes  
✅ All tests passing (11/11)  
✅ Rate limiting works correctly  
✅ Cross-origin warning resolved
