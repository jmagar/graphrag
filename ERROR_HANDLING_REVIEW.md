# GraphRAG Error Handling Review - Comprehensive Analysis

## Executive Summary

This codebase violates the "throw errors early, no fallbacks" philosophy in several critical areas. The main violations are:

1. **Defensive fallback patterns** instead of failing fast (Redis, GraphDB)
2. **Blanket exception catching** with generic 500 status codes instead of differentiated HTTP responses
3. **Silent error swallowing** in cache and persistence layers
4. **Missing error type differentiation** (client vs server errors, timeouts vs unavailable)
5. **Returning error objects** from endpoints instead of raising HTTPExceptions
6. **Optional service handling** that masks configuration problems

---

## BACKEND ERROR HANDLING VIOLATIONS

### CRITICAL: Defensive Fallback Patterns

#### 1. main.py - Redis Connection (Lines 95-100)
**Severity**: MEDIUM  
**Philosophy Violation**: Defensive fallback - logs warning but continues without service

```python
try:
    await redis_service.client.ping()
    redis_available = True
    logger.info("  ✅ Redis connection verified")
except Exception as e:
    logger.warning("  ⚠️  Redis unavailable: %s", e)  # FALLBACK: Continues
```

**Issue**: Per guidelines: "Throw errors early, do not use fallbacks"
- Redis becomes optional instead of failing fast
- Application continues with degraded functionality without explicit user knowledge
- QueryCache is silently disabled (lines 103-122)
- Masks configuration/deployment problems

**Impact**: 
- Silent feature degradation (caching doesn't work)
- Users don't know cache is disabled
- Difficult to debug in production

**Recommendation**: Let the exception propagate. Redis should be treated as required if ENABLE_QUERY_CACHE=true.

---

#### 2. redis_service.py - Constructor (Lines 21-38)
**Severity**: MEDIUM  
**Philosophy Violation**: Defensive fallback in initialization

```python
def __init__(self):
    try:
        self.client = redis.Redis(...)
        self._available = True
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without Redis.")
        self.client = None  # FALLBACK
        self._available = False
```

**Issue**: 
- Creates disabled Redis client instead of raising
- All methods silently degrade (return False/empty on error)
- No clear failure signal to application

**Recommendation**: Raise the exception. Let the application handle Redis unavailability explicitly.

---

#### 3. graph_db.py - GraphDB Connection (Referenced in main.py)
**Severity**: MEDIUM  
**Philosophy Violation**: Similar defensive fallback pattern

```python
logger.warning("⚠️ GraphDB features will be unavailable, but API will continue")
```

**Issue**: GraphDB gracefully degrades but user never knows.

---

### CRITICAL: Blanket Exception Catching with Wrong Status Codes

#### 4. crawl.py - All Endpoints (Lines 109-110, 125-126, 137-138)
**Severity**: HIGH  
**Philosophy Violation**: Generic exception catching loses error type information

```python
@router.post("/", response_model=CrawlResponse)
async def start_crawl(...):
    try:
        result = await firecrawl_service.start_crawl(crawl_options)
        return {...}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start crawl: {str(e)}")
        # ^ All errors return 500, even if they should be 503, 504, 400, etc.
```

**Issues**:
- **All** exceptions → 500 (Internal Server Error)
- Should differentiate:
  - `httpx.ConnectError` → 503 (Service Unavailable)
  - `httpx.TimeoutException` → 504 (Gateway Timeout)
  - `httpx.HTTPStatusError` (4xx) → 400 (Bad Request)
  - `httpx.HTTPStatusError` (5xx) → 502 (Bad Gateway)
  - `ValueError` (invalid URL) → 400 (Bad Request)

**Endpoints with this pattern**:
- POST /api/v1/crawl (line 110)
- GET /api/v1/crawl/{id} (line 126)
- DELETE /api/v1/crawl/{id} (line 138)
- GET /api/v1/query (line 105)
- GET /api/v1/query/collection/info (line 115)
- POST /api/v1/search (line 86)
- POST /api/v1/map (line 53)
- POST /api/v1/cache/stats (line 47)
- DELETE /api/v1/cache/invalidate/all (line 72)

**Recommendation**: Implement type-specific error handling like `extract.py` does (lines 82-105).

---

#### 5. query.py - Missing Status Code Differentiation (Lines 104-105)
**Severity**: HIGH

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
```

**Should handle**:
- Embedding generation failure → 503 (Service Unavailable - TEI down)
- Vector search failure → 503 (Service Unavailable - Qdrant down)
- LLM generation failure → 503 (Service Unavailable - Ollama down)
- Invalid query → 400 (Bad Request)
- Timeout → 504 (Gateway Timeout)

---

#### 6. search.py - Blanket Error Handling (Line 85-86)
**Severity**: HIGH

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")
```

**Context**: Firecrawl search can fail with network errors, timeouts, rate limits, etc.

---

### CRITICAL: Silent Error Swallowing (Cache Layer)

#### 7. query_cache.py - Cache Errors Silently Ignored (Lines 103-106)
**Severity**: HIGH  
**Philosophy Violation**: Returns None instead of raising

```python
try:
    key = self._generate_cache_key(collection, query_text, **params)
    data = await self.redis.get(key)
    if data:
        self._stats["hits"] += 1
        cached = json.loads(data)
        ...
except Exception as e:
    logger.warning(f"Cache get error: {e}")  # Logs but doesn't raise
    self._stats["misses"] += 1
    return None  # SILENT FALLBACK
```

**Issues**:
- Cache errors are silently treated as cache misses
- Application doesn't know cache is broken
- Impossible to distinguish "not in cache" from "cache failure"
- Masks Redis/persistence problems
- Violates "throw errors early" philosophy

**Recommendation**: Let cache errors propagate OR return error indicator that can be handled.

---

#### 8. redis_service.py - All Methods Return False on Error (Lines 50-117)
**Severity**: MEDIUM  
**Philosophy Violation**: Silent error swallowing pattern

```python
async def mark_page_processed(self, crawl_id: str, source_url: str) -> bool:
    if not await self.is_available():
        logger.debug("Redis unavailable, skipping page tracking")
        return False
    
    try:
        key = f"crawl:{crawl_id}:processed"
        await self.client.sadd(key, source_url)
        await self.client.expire(key, 3600)
        return True
    except Exception as e:
        logger.error(f"Failed to mark page as processed: {e}")
        return False  # SILENT FALLBACK - caller doesn't know what happened
```

**Issues**:
- Returns `False` on both "unavailable" and "error"
- Caller can't distinguish between Redis being down vs not available
- Page deduplication silently fails
- Webhook processing assumes page was marked but it wasn't

**Impact on webhooks.py**:
- Line 218: `await redis.mark_page_processed(crawl_id, source_url)` - error silently ignored
- Line 243: `if await redis.is_page_processed(...)` - might return False if Redis error occurred
- Pages could be processed twice if Redis fails during marking

---

### CRITICAL: Returning Error Objects Instead of Raising HTTPException

#### 9. webhooks.py - JSON Parse Errors (Lines 148-160)
**Severity**: HIGH  
**Philosophy Violation**: Returns error object instead of raising HTTPException

```python
try:
    payload_dict = json.loads(body.decode("utf-8"))
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in webhook payload: {e}")
    return {"status": "error", "error": "Invalid JSON payload"}  # WRONG: Should raise
```

**Issues**:
- Returns 200 OK with error in body (incorrect HTTP semantics)
- Should raise HTTPException with 400 status
- Firecrawl will think webhook succeeded
- Two locations with this pattern (lines 152, 160)
- Masks JSON decoding errors with generic message

**Also**:
- Line 343: `return {"status": "error", "error": error}` for crawl.failed event
  - This is actually a legitimate success response for a failed crawl event
  - But it returns 200 OK which is semantically correct for webhook acknowledgment

---

### MODERATE: Missing Error Type Differentiation

#### 10. extract.py - Good Example of Proper Error Handling (Lines 82-105)
**Status**: GOOD - Use as template

```python
except (ValueError, TypeError) as e:
    logger.exception("Validation error during extraction")
    raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

except asyncio.TimeoutError:
    logger.exception("Timeout error during extraction")
    raise HTTPException(status_code=504, detail="Extraction request timed out...")

except aiohttp.ClientError:
    logger.exception("Network error during extraction")
    raise HTTPException(status_code=502, detail="Failed to connect to extraction service")

except KeyError as e:
    logger.exception("Data parsing error during extraction")
    raise HTTPException(status_code=422, detail=f"Invalid response structure: {str(e)}")

except Exception as e:
    logger.exception("Unexpected error during extraction")
    raise HTTPException(status_code=500, detail=f"Failed to extract data: {str(e)}")
```

**This is the pattern other endpoints should follow.**

---

#### 11. scrape.py - Partial Implementation (Lines 88-98)
**Status**: PARTIAL - Good but could be better

```python
except TimeoutException as e:
    logger.error(f"Timeout scraping URL {request.url}: {e}")
    raise HTTPException(status_code=504, detail="Request timeout while scraping URL")

except HTTPStatusError as e:
    logger.error(f"HTTP error scraping URL {request.url}: {e}")
    raise HTTPException(status_code=502, detail=f"Firecrawl API error: {str(e)}")

except Exception:
    logger.exception(f"Unexpected error scraping URL {request.url}")
    raise HTTPException(status_code=500, detail="Internal server error while scraping URL")
```

**Issues**:
- HTTPStatusError returns 502 for ALL status codes
- Should differentiate 4xx (400) vs 5xx (502)
- Missing handling for other httpx exceptions (ConnectError, etc.)

---

### MODERATE: Resilience Module Error Handling

#### 12. resilience.py - Persistence Backend Errors (Lines 150-151, 160-169)
**Severity**: LOW  
**Philosophy Violation**: Swallows circuit breaker state persistence errors

```python
try:
    state_data = await self.persistence_backend.load_state(self.name)
    ...
except Exception as e:
    logger.warning(f"Failed to load circuit breaker state for {self.name}: {e}")
    # Continues with default state

try:
    state_data = {...}
    await self.persistence_backend.save_state(self.name, state_data)
except Exception as e:
    logger.warning(f"Failed to sync circuit breaker state for {self.name}: {e}")
    # Continues without persisting
```

**Issues**:
- Circuit breaker state loss on Redis error
- Fire-and-forget pattern with asyncio.create_task() (line 181, 194, 214)
  - Errors in background tasks are lost
  - No error handling for the async task

**Recommendation**: Either ensure persistence works or fail fast.

---

## FRONTEND ERROR HANDLING VIOLATIONS

### MODERATE: Defensive Fallback in Health Check

#### 13. health/route.ts - Silent Degradation (Lines 42-48, 73-76)
**Severity**: MEDIUM  
**Philosophy Violation**: Catches all errors and returns 503

```typescript
try {
    const response = await fetch(`${API_BASE_URL}/health`, {
        method: "GET",
        headers: {"Content-Type": "application/json"},
        cache: "no-store",
    });

    if (!response.ok) {
        return NextResponse.json(
            { error: "Backend unhealthy", status: response.status },
            { status: response.status }
        );
    }
    const data = await response.json();
    return NextResponse.json(data);
} catch (error) {
    console.error("Health check error:", error);
    return NextResponse.json(
        { error: "Failed to connect to backend" },
        { status: 503 }  // All errors -> 503, even if error is on frontend
    );
}
```

**Issues**:
- Network errors treated same as backend being down
- JSON parse errors on valid response → 503
- Frontend errors (e.g., out of memory) → 503
- Doesn't distinguish different failure modes

---

#### 14. chat/route.ts - Error Handling in Stream (Lines 130-138)
**Severity**: MEDIUM  
**Status**: Acceptable for streaming, but has tradeoffs

```typescript
} catch (error: unknown) {
    console.error("Chat error:", error);
    const errorMessage = error instanceof Error ? error.message : "An error occurred";
    const errorData = JSON.stringify({
        type: "error",
        error: errorMessage,
    });
    sse.send(`data: ${errorData}\n\n`);  // Sends error in stream
    sse.close();
}
```

**Issues**:
- Errors sent as SSE messages instead of HTTP status codes
- Response was 200 OK but stream contains error
- Client must parse SSE stream to find errors
- Acceptable for streaming but loses HTTP semantics

---

#### 15. useSystemStatus.ts - Silent Error Handling (Lines 99-111)
**Status**: GOOD - Appropriate for monitoring

```typescript
const checkConnectivity = async () => {
    try {
        const response = await fetch('/api/health', { method: 'HEAD' });
        if (!response.ok) {
            showError('API connection lost. Some features may be unavailable.', {
                dismissible: true,
            });
        }
    } catch (error) {
        showError('Unable to connect to API. Check your internet connection.', {
            dismissible: true,
        });
    }
};
```

**This is appropriate**: It's monitoring/notification code, not critical path.

---

#### 16. crawl/route.ts - Good Error Handling
**Status**: GOOD

```typescript
try {
    const body = await req.json();

    if (!body.url) {
        return NextResponse.json({ error: 'URL is required' }, { status: 400 });
    }

    const response = await axios.post(
        `${backendUrl}/api/v1/crawl/`,
        body
    );

    return NextResponse.json(response.data);
} catch (error: unknown) {
    if (axios.isAxiosError(error)) {
        console.error('Crawl error:', error.response?.data || error.message);
        return NextResponse.json(
            { error: error.response?.data?.detail || 'Failed to start crawl' },
            { status: error.response?.status || 500 }
        );
    }
    const errorMessage = error instanceof Error ? error.message : 'Failed to start crawl';
    console.error('Crawl error:', errorMessage);
    return NextResponse.json(
        { error: errorMessage },
        { status: 500 }
    );
}
```

**Good points**:
- Validates input early (400)
- Propagates backend status codes
- Distinguishes axios errors from others
- Includes error details in response

---

## MISSING ERROR CASES & COVERAGE GAPS

### 1. No HTTP Status Code Differentiation
**Summary**: Endpoints should map errors to appropriate HTTP status codes

```
400 Bad Request    ← Input validation, malformed requests
401 Unauthorized   ← Auth failures (partially implemented in webhooks)
403 Forbidden      ← Permission denied (not implemented)
404 Not Found      ← Resource not found (few places implement this)
422 Unprocessable  ← Validation failures (extract.py implements this)
429 Too Many Requests ← Rate limiting (not implemented)
500 Internal Error ← Server errors
502 Bad Gateway    ← Upstream service errors (few places)
503 Unavailable    ← Service down (not differentiated)
504 Timeout        ← Timeout errors (scrape.py, extract.py implement)
```

**Affected endpoints**: crawl.py, query.py, search.py, map.py, cache.py, graph.py

---

### 2. No Service-Specific Error Handling
**Summary**: Different services have different failure modes

**Firecrawl API errors**:
- 429 (Rate limited) should return 429, not 500
- 4xx (Invalid request) should return 400, not 500
- 5xx (Service error) should return 502, not 500
- Connection timeouts should return 504, not 500

**Current**: All become 500

**Qdrant errors**:
- Collection not found → 404
- Invalid query → 400
- Service down → 503
- Current: All become 500

**TEI/Embedding errors**:
- Service down → 503
- Invalid input → 400
- Timeout → 504
- Current: All become 500

---

### 3. No Detailed Error Messages
**Summary**: Error messages are too generic to be actionable

**Current**:
```
"Failed to start crawl: Connection refused"
"Query failed: Service unavailable"
"Failed to search: timeout"
```

**Should be**:
```
"Failed to connect to Firecrawl at http://localhost:4200: Connection refused"
"Query failed: TEI embedding service (http://localhost:4207) unavailable"
"Search timed out after 60s. Check Firecrawl service health."
```

---

### 4. Missing Validation Error Clarity
**Summary**: Pydantic validation errors not properly formatted

**Issues**:
- Validation errors should return 422 (Unprocessable Entity)
- Error messages should identify which field is invalid
- Should suggest valid formats

**Example: CrawlRequest validation**:
```python
url: HttpUrl  # If invalid, what error message?
maxDiscoveryDepth: Optional[int] = None  # Range checks?
limit: Optional[int] = 10000  # Max value error message?
```

---

### 5. No Background Task Error Visibility
**Summary**: Errors in background tasks are silently logged

**Locations**:
- crawl.py: `background_tasks.add_task(...)`
- scrape.py: `background_tasks.add_task(...)`
- search.py: `background_tasks.add_task(...)`
- extract.py: `background_tasks.add_task(...)`
- webhooks.py: `background_tasks.add_task(...)`

**Issues**:
- Document processing errors don't reach user
- But endpoint already returned 200 OK
- Webhook already acknowledged to Firecrawl
- User never knows documents weren't stored

**Recommendation**: Log errors with context and metrics, but this is inherent to background tasks.

---

### 6. No Cache Invalidation Error Handling
**Summary**: Cache errors cascade without visibility

**Flow**:
1. Query → TEI embedding
2. Vector search (may be cached)
3. If cache error occurs:
   - query_cache.get() returns None (miss)
   - Vector search executes
   - Results are cached (may also fail)
   - All errors silently swallowed

**Risk**: Cache broken and user doesn't know.

---

### 7. No Rate Limiting Error Handling
**Summary**: Rate limits not explicitly handled

**Issues**:
- Firecrawl returns 429 → endpoint returns 500
- Should return 429
- No rate limit error messages or retry-after headers

---

## ERROR LOGGING & MONITORING GAPS

### Missing Structured Logging
**Current**:
```python
logger.error(f"Failed to process: {str(e)}")
```

**Should be**:
```python
logger.error(
    "Processing failed",
    exc_info=True,  # Include full stack trace
    extra={
        "service": "firecrawl",
        "operation": "start_crawl",
        "url": request.url,
        "error_type": type(e).__name__,
        "error_code": getattr(e, "status_code", None),
    }
)
```

---

### Missing Monitoring
**Not implemented**:
1. Error rate metrics by endpoint
2. Error rate metrics by service (Firecrawl, Qdrant, TEI, Ollama, Redis)
3. Cache hit/miss rates (not exposed via API)
4. Circuit breaker state metrics
5. Alerting on error rate thresholds
6. Error categorization (client vs server errors)

---

### Missing Error Context
**Issues**:
- Errors don't include request ID for tracing
- No correlation IDs across services
- No timing information for timeout errors
- No service health status in error responses

---

## EXCEPTION PROPAGATION PATTERNS

### GOOD: Services Let Exceptions Propagate
**Examples**:
- `EmbeddingsService.generate_embeddings()` - lets httpx.HTTPStatusError propagate
- `VectorDBService.search()` - lets qdrant errors propagate
- `FirecrawlService.*()` methods - let errors propagate with circuit breaker

---

### BAD: Endpoints Catch Everything
**Pattern**:
```python
@router.post("/")
async def endpoint(...):
    try:
        # Do something
    except Exception as e:
        raise HTTPException(status_code=500, ...)  # All exceptions → 500
```

**Better pattern (from extract.py)**:
```python
@router.post("/")
async def endpoint(...):
    try:
        # Do something
    except SpecificError as e:
        raise HTTPException(status_code=ABC, ...)
    except AnotherError as e:
        raise HTTPException(status_code=XYZ, ...)
    except Exception as e:
        raise HTTPException(status_code=500, ...)  # Only here
```

---

## VIOLATIONS SUMMARY TABLE

| File | Issue | Severity | Type | Line(s) |
|------|-------|----------|------|---------|
| main.py | Defensive Redis fallback | MEDIUM | Fallback | 95-100 |
| main.py | Shutdown error suppression | MEDIUM | Suppression | 207-228 |
| redis_service.py | Defensive client initialization | MEDIUM | Fallback | 21-38 |
| redis_service.py | Silent error returns | MEDIUM | Swallowing | 50-117 |
| query_cache.py | Cache errors ignored | HIGH | Swallowing | 103-106 |
| resilience.py | Persistence errors ignored | LOW | Swallowing | 150-151, 160-169 |
| crawl.py | Blanket 500 status | HIGH | Wrong Status | 109, 126, 138 |
| query.py | Blanket 500 status | HIGH | Wrong Status | 104, 115 |
| search.py | Blanket 500 status | HIGH | Wrong Status | 85 |
| map.py | Blanket 500 status | HIGH | Wrong Status | 52 |
| cache.py | Blanket 500 status | HIGH | Wrong Status | 47, 72 |
| graph.py | Blanket 500 status | HIGH | Wrong Status | Generic |
| scrape.py | Partial diff. (4xx/5xx) | MEDIUM | Incomplete | 88-98 |
| extract.py | Good pattern (ref) | GOOD | Template | 82-105 |
| chat.py | Streaming error handling | MEDIUM | Semantic | 130-138 |
| webhooks.py | Returns error object | HIGH | Wrong Pattern | 152, 160 |
| health/route.ts | Defensive fallback | MEDIUM | Fallback | 42-48, 73-76 |
| crawl/route.ts | Good pattern (ref) | GOOD | Template | Various |

---

## RECOMMENDATIONS

### Priority 1: Critical Fixes (Violate Core Philosophy)

1. **Fix Defensive Fallbacks**
   - main.py: Let Redis connection error propagate if ENABLE_QUERY_CACHE=true
   - redis_service.py: Raise error instead of creating disabled client
   - Require explicit handling of optional services

2. **Fix Blanket Exception Catching**
   - Implement type-specific error handling in all endpoints
   - Use extract.py (lines 82-105) as template
   - Map service errors to correct HTTP status codes

3. **Fix Silent Error Swallowing**
   - query_cache.py: Raise errors instead of returning None
   - redis_service.py: Raise errors instead of returning False
   - resilience.py: Handle persistence failures explicitly

4. **Fix Wrong HTTP Status Codes**
   - crawl.py, query.py, search.py, map.py, cache.py: Differentiate status codes
   - 503 for service unavailable
   - 504 for timeouts
   - 400 for client errors
   - 502 for bad gateway

### Priority 2: Important Improvements

5. **Improve Error Messages**
   - Include service name and URL in errors
   - Provide actionable guidance
   - Include error codes/details from services

6. **Fix Webhook Error Handling**
   - webhooks.py lines 152, 160: Raise HTTPException instead of returning error object
   - Maintain 200 OK for webhook acknowledgment but fix JSON errors

7. **Add Structured Logging**
   - Include error type, service, operation, stack trace
   - Add request/correlation IDs
   - Track metrics per service/endpoint

### Priority 3: Future Improvements

8. **Implement Error Monitoring**
   - Track error rates by endpoint and service
   - Monitor cache performance
   - Alert on error rate thresholds
   - Expose cache statistics via API

9. **Add Rate Limit Handling**
   - Detect 429 responses
   - Return 429 to clients
   - Include Retry-After headers

10. **Improve Background Task Error Visibility**
    - Log errors with full context
    - Track success/failure metrics
    - Consider circuit breaker for failing tasks

---

## CODE EXAMPLES

### Example 1: Before (Bad) → After (Good)

**Before (crawl.py lines 109-110)**:
```python
try:
    result = await firecrawl_service.start_crawl(crawl_options)
    # ...
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to start crawl: {str(e)}")
```

**After**:
```python
try:
    result = await firecrawl_service.start_crawl(crawl_options)
    # ...
except httpx.ConnectError as e:
    logger.error(
        "Failed to connect to Firecrawl service",
        exc_info=True,
        extra={"service": "firecrawl", "url": crawl_options["url"]}
    )
    raise HTTPException(
        status_code=503,
        detail=f"Firecrawl service unavailable: {settings.FIRECRAWL_URL}"
    )
except httpx.TimeoutException as e:
    logger.error("Firecrawl request timeout", exc_info=True)
    raise HTTPException(
        status_code=504,
        detail="Firecrawl request timed out after 30s"
    )
except httpx.HTTPStatusError as e:
    if 400 <= e.response.status_code < 500:
        logger.warning("Invalid crawl request", extra={"url": crawl_options["url"]})
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {e.response.text}"
        )
    else:
        logger.error("Firecrawl API error", extra={"status": e.response.status_code})
        raise HTTPException(
            status_code=502,
            detail=f"Firecrawl API error (HTTP {e.response.status_code})"
        )
except ValueError as e:
    raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
except Exception as e:
    logger.exception(
        "Unexpected error starting crawl",
        extra={"error_type": type(e).__name__}
    )
    raise HTTPException(
        status_code=500,
        detail="Internal server error while starting crawl"
    )
```

---

### Example 2: Before (Bad) → After (Good)

**Before (redis_service.py lines 50-73)**:
```python
async def mark_page_processed(self, crawl_id: str, source_url: str) -> bool:
    if not await self.is_available():
        logger.debug("Redis unavailable, skipping page tracking")
        return False  # Caller doesn't know if it failed

    try:
        key = f"crawl:{crawl_id}:processed"
        await self.client.sadd(key, source_url)
        await self.client.expire(key, 3600)
        logger.debug(f"Marked page as processed: {source_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to mark page as processed: {e}")
        return False  # Caller doesn't know what happened
```

**After** (Option 1 - Explicit handling):
```python
async def mark_page_processed(self, crawl_id: str, source_url: str) -> None:
    """Mark a page as processed for a crawl. Raises exception on failure."""
    if not self.client:
        raise RuntimeError("Redis not initialized. Check configuration.")
    
    try:
        key = f"crawl:{crawl_id}:processed"
        await self.client.sadd(key, source_url)
        await self.client.expire(key, 3600)
        logger.debug(f"Marked page as processed: {source_url}")
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error while marking page: {e}")
        raise RuntimeError("Failed to mark page: Redis connection error") from e
    except Exception as e:
        logger.error(f"Failed to mark page as processed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to mark page: {type(e).__name__}") from e
```

**After** (Option 2 - With fallback behavior if needed):
```python
async def mark_page_processed(
    self, crawl_id: str, source_url: str, fail_on_error: bool = True
) -> bool:
    """
    Mark a page as processed.
    
    Args:
        crawl_id: Crawl job ID
        source_url: Source URL
        fail_on_error: If True, raise on error. If False, log and return False.
    
    Returns:
        True if marked successfully
        
    Raises:
        RuntimeError: If fail_on_error=True and error occurs
    """
    if not self.client:
        if fail_on_error:
            raise RuntimeError("Redis not initialized")
        logger.warning("Redis not available, skipping page tracking")
        return False
    
    try:
        key = f"crawl:{crawl_id}:processed"
        await self.client.sadd(key, source_url)
        await self.client.expire(key, 3600)
        return True
    except Exception as e:
        if fail_on_error:
            logger.error(f"Failed to mark page: {e}", exc_info=True)
            raise RuntimeError(f"Redis error: {type(e).__name__}") from e
        else:
            logger.warning(f"Failed to mark page (continuing): {e}")
            return False
```

---

## TESTING RECOMMENDATIONS

### Test Cases to Add

1. **Service Unavailability**
   - Test each endpoint when backend service is down
   - Verify 503 status code
   - Verify error message mentions service name

2. **Timeouts**
   - Mock slow responses
   - Verify 504 status code
   - Verify timeout error message

3. **Invalid Requests**
   - Test with invalid input
   - Verify 400 status code
   - Verify error identifies which field is invalid

4. **Cache Failures**
   - Mock Redis connection error
   - Verify graceful degradation (if allowed)
   - Or verify failure (if cache required)

5. **Error Message Quality**
   - Verify error messages are actionable
   - Verify error messages identify the problem
   - Verify error messages include service details

---

## CONCLUSION

The codebase violates the "throw errors early, no fallbacks" philosophy in several critical areas:

1. **Main issues**: Defensive fallbacks, blanket exceptions, silent error swallowing
2. **High priority**: Fix exceptions and status codes to match HTTP semantics
3. **Medium priority**: Improve error messages and add structured logging
4. **Low priority**: Add monitoring and metrics

The recommended approach is to:
- Fail fast when services are required
- Distinguish error types with appropriate HTTP status codes
- Provide clear, actionable error messages
- Log errors with full context for debugging
- Never silently swallow errors that affect functionality

Extract.py (lines 82-105) demonstrates the correct pattern and should be used as a template for all endpoints.
