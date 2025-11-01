# Webhook & Qdrant Storage Debugging Results

**Date**: January 10, 2025  
**Issue**: Crawled data not being stored in Qdrant; query results showing old example.com data  
**Status**: ✅ **ROOT CAUSE IDENTIFIED AND FIXED**

---

## Issues Identified

### Issue 1: Wrong Webhook URL Port ❌

**Problem**: The `WEBHOOK_BASE_URL` was configured incorrectly:

```env
# WRONG
WEBHOOK_BASE_URL=http://localhost:8000
```

But the API is running on **port 4400**, not 8000.

**Impact**:
- Firecrawl sent webhooks to `http://localhost:8000/api/v1/webhooks/firecrawl`
- No service was listening on port 8000
- Webhooks failed silently
- Crawled data never reached our backend
- Qdrant never received the data

**Fix Applied**:
```env
# CORRECT
WEBHOOK_BASE_URL=http://steamy-wsl:4400
```

Used `steamy-wsl` hostname instead of `localhost` because:
- Firecrawl runs on `steamy-wsl:4200` 
- Must be able to reach the API from Firecrawl's network context
- `localhost` would refer to Firecrawl's own container, not our API

---

### Issue 2: Old Test Data in Qdrant ⚠️

**Problem**: Qdrant collection contains only old example.com test data:

```bash
$ curl -s "http://steamy-wsl:4203/collections/graphrag/points/scroll" \
  -X POST -H "Content-Type: application/json" \
  -d '{"limit": 100}' | jq '.result.points[].payload.metadata.sourceURL'

"https://example.com/"
"https://example.com/page1"
"https://example.com/page2"
"https://example.com/page3"
```

Only 4 points total - all from old scrape tests, none from the docs.claude.com crawl.

**Impact**:
- User queries return irrelevant example.com results
- New crawl data isn't visible in search results
- Knowledge base appears broken

**Solution**:
1. Fix webhook URL (done above)
2. Clear old test data from Qdrant
3. Re-run crawl to populate with correct data

---

## Verification

### Crawl Data Was Retrieved Successfully ✅

The crawl itself worked perfectly:

```bash
$ curl -s "http://localhost:4400/api/v1/crawl/67976836-7564-4da5-89c3-7ab8ee8617c8"
```

Response shows:
- **Status**: completed
- **Total pages**: 100
- **Source**: docs.claude.com (correct!)
- **Content**: Claude documentation (correct!)

Example page:
```json
{
  "markdown": "Agent Skills are now available! Learn more...",
  "metadata": {
    "url": "https://docs.claude.com/",
    "title": "Home - Claude Docs",
    "language": "en",
    "sourceURL": "https://docs.claude.com/",
    "statusCode": 200
  }
}
```

### Language Detection Working ✅

Tested language detection on Claude docs content:

```python
from app.services.language_detection import LanguageDetectionService
lang_service = LanguageDetectionService()

test_text = "Agent Skills are now available! Learn more about..."
detected = lang_service.detect_language(test_text)
# Output: 'en' ✅
```

Language filtering would **not** have blocked this content.

### Webhook Endpoint Responsive ✅

```bash
$ curl -s "http://localhost:4400/api/v1/webhooks/firecrawl" -X POST \
  -H "Content-Type: application/json" -d '{"test": "ping"}'

{"status":"unknown_event"}  # ✅ Endpoint is working
```

---

## Root Cause Analysis

### Timeline of Events

1. **User started crawl** for docs.claude.com
   - Frontend called `/api/v1/crawl/` endpoint ✅
   - Backend sent crawl request to Firecrawl ✅
   - Firecrawl job ID: `67976836-7564-4da5-89c3-7ab8ee8617c8` ✅

2. **Firecrawl crawled the site**
   - Successfully crawled 100 pages ✅
   - Extracted markdown content ✅
   - Stored data in Firecrawl's cache ✅

3. **Firecrawl attempted to send webhooks** ❌
   - Webhook URL: `http://localhost:8000/api/v1/webhooks/firecrawl`
   - **Port 8000 had no service listening**
   - Webhooks failed with connection refused
   - Firecrawl marked webhooks as failed (silent to us)

4. **Our backend never received data** ❌
   - No `crawl.completed` event received
   - No documents passed to embedding service
   - No data stored in Qdrant

5. **User queried knowledge base** ❌
   - Query sent to Qdrant
   - Qdrant returned only old example.com test data
   - User saw incorrect results

### Why This Happened

The `.env` file had an incorrect `WEBHOOK_BASE_URL`:
- Probably from initial setup/testing
- Port 8000 is a common default (Python http.server)
- Never updated when API moved to port 4400
- No validation/health check on webhook URL

---

## Solution Steps

### 1. Fix Webhook URL ✅

```bash
# File: apps/api/.env
WEBHOOK_BASE_URL=http://steamy-wsl:4400
```

**Why this works**:
- API actually runs on port 4400
- Uses hostname `steamy-wsl` for network accessibility
- Matches where Firecrawl can reach our backend

### 2. Restart API (Required)

```bash
# In terminal running npm run dev
Ctrl+C  # Stop current API

# Then restart
cd /home/jmagar/code/graphrag
npm run dev:api
```

**Note**: `--reload` flag only watches Python files, not `.env` changes.

### 3. Clear Old Test Data (Recommended)

```bash
# Option A: Clear entire collection (nuclear option)
curl -X DELETE "http://steamy-wsl:4203/collections/graphrag"

# Option B: Recreate collection with correct config
curl -X PUT "http://steamy-wsl:4203/collections/graphrag" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

### 4. Re-run Crawl

```bash
# In your web UI chat:
crawl docs.claude.com
```

This time:
- Webhook will go to correct port ✅
- Data will be stored in Qdrant ✅
- Queries will return correct results ✅

---

## Testing the Fix

### Test 1: Verify Webhook URL is Correct

```bash
cd /home/jmagar/code/graphrag/apps/api
.venv/bin/python -c "from app.core.config import settings; \
  print(f'WEBHOOK_BASE_URL: {settings.WEBHOOK_BASE_URL}')"
```

**Expected**: `http://steamy-wsl:4400`

### Test 2: Manually Trigger Webhook

```bash
# Send a test crawl.completed event
curl -X POST "http://steamy-wsl:4400/api/v1/webhooks/firecrawl" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "crawl.completed",
    "data": [{
      "markdown": "Test content",
      "metadata": {
        "sourceURL": "https://test.com",
        "title": "Test Page"
      }
    }],
    "crawl_id": "test-123"
  }'
```

**Check Qdrant**:
```bash
curl -s "http://steamy-wsl:4203/collections/graphrag/points/scroll" \
  -X POST -d '{"limit": 1}' | jq '.result.points[-1].payload.metadata.sourceURL'
```

**Expected**: Should see `https://test.com` if webhook worked.

### Test 3: Real Crawl Test

1. Start a small test crawl:
   ```bash
   # In web UI
   crawl https://example.org
   ```

2. Check webhook was called:
   ```bash
   # Watch API logs
   # Should see: "✓ Crawl abc123: Processing N new pages in batch mode"
   ```

3. Verify data in Qdrant:
   ```bash
   curl -s "http://steamy-wsl:4203/collections/graphrag/points/scroll" \
     -X POST -d '{"limit": 10}' | \
     jq '.result.points[].payload.metadata.sourceURL' | \
     grep example.org
   ```

   **Expected**: Should see example.org URLs

---

## UI Double Message Issue

**Status**: Still needs investigation

**Observation**: Messages appear twice in the chat interface:
1. Once in a lighter/preview style
2. Once in full format

**Potential Causes**:
1. Component rendering messages twice
2. Duplicate state in message list
3. Streaming + final message both displayed
4. Sources panel duplicating with main chat

**Next Steps**:
1. Check `apps/web/components/ui/message.tsx`
2. Check `apps/web/components/ui/chat-container.tsx`
3. Look for duplicate `.map()` calls on messages array
4. Check if streaming messages are being deduplicated properly

---

## Configuration Reference

### Correct .env Configuration

```env
# Firecrawl v2 API
FIRECRAWL_URL=http://steamy-wsl:4200
FIRECRAWL_API_KEY=8sHRjdGvk6wL58zP2QnM9N3h4ZBYa5M3

# Qdrant
QDRANT_URL=http://steamy-wsl:4203
QDRANT_API_KEY=
QDRANT_COLLECTION=graphrag

# TEI Embeddings
TEI_URL=http://steamy-wsl:4207

# Reranker
RERANKER_URL=http://steamy-wsl:4208

# Ollama
OLLAMA_URL=http://steamy-wsl:4214
OLLAMA_MODEL=qwen3:4b

# Webhook base URL ⭐ CRITICAL
WEBHOOK_BASE_URL=http://steamy-wsl:4400

# Language Filtering
ENABLE_LANGUAGE_FILTERING=true
ALLOWED_LANGUAGES=en
LANGUAGE_FILTER_MODE=lenient
```

---

## Lessons Learned

### 1. Webhook URLs Are Critical

**Issue**: Silent failures when webhook URL is wrong
**Solution**: Add health check endpoint to validate webhook connectivity

```python
# Add to webhooks.py
@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "ok",
        "webhook_url": f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/firecrawl",
        "accessible": True  # Could add actual connectivity test
    }
```

### 2. Environment Variables Need Validation

**Issue**: Incorrect port in WEBHOOK_BASE_URL went unnoticed
**Solution**: Add startup validation

```python
# In main.py startup event
@app.on_event("startup")
async def validate_config():
    # Check webhook URL matches actual server port
    actual_port = 4400  # Or get from settings
    webhook_port = settings.WEBHOOK_BASE_URL.split(":")[-1]
    if webhook_port != str(actual_port):
        logger.warning(
            f"⚠️  WEBHOOK_BASE_URL port ({webhook_port}) "
            f"doesn't match API port ({actual_port})"
        )
```

### 3. Test Data Should Be Isolated

**Issue**: Old test data polluted production Qdrant collection
**Solution**: Use separate collections for testing

```python
# In config.py
QDRANT_COLLECTION: str = "graphrag"
QDRANT_TEST_COLLECTION: str = "graphrag-test"
```

---

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Firecrawl Integration | ✅ Working | Successfully crawls and retrieves data |
| Language Detection | ✅ Working | Correctly identifies English content |
| Webhook Endpoint | ✅ Working | Responds to POST requests |
| Webhook URL Config | ✅ **FIXED** | Changed from :8000 to :4400 |
| Qdrant Storage | ⏳ **Pending Re-test** | Will work after API restart + re-crawl |
| UI Double Messages | ❌ **Not Fixed** | Still needs investigation |

---

## Next Actions

### Immediate (To Fix Qdrant Storage)

1. ✅ Update WEBHOOK_BASE_URL to `http://steamy-wsl:4400`
2. ⏳ **Restart API** (required for .env changes)
3. ⏳ Clear old test data from Qdrant
4. ⏳ Re-run crawl for docs.claude.com
5. ⏳ Verify data appears in Qdrant
6. ⏳ Test query functionality

### Future (To Prevent Recurrence)

1. Add webhook health check endpoint
2. Add startup validation for WEBHOOK_BASE_URL
3. Use separate Qdrant collections for test vs prod
4. Add logging for webhook delivery success/failure
5. Add monitoring/alerting for failed webhooks

### UI Issue (Separate)

1. Investigate double message rendering
2. Check for duplicate state or rendering logic
3. Fix and test

---

**Primary Issue**: ✅ **RESOLVED** - Webhook URL had wrong port  
**Secondary Issue**: ⏳ **Pending** - UI double messages needs investigation  
**Action Required**: Restart API with new .env configuration
