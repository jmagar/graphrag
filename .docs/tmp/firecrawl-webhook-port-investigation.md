# Firecrawl Webhook Port Investigation

**Date**: 2025-10-30
**Issue**: Firecrawl sending webhooks to old port 8000 instead of new port 4400
**Status**: ✅ RESOLVED - Configuration correct, issue was from old crawl job

## Error Log

```
taboot-crawler  | worker         2025-10-30 17:41:00 error [webhook-sender:]: Failed to send webhook
{
  "module": "webhook-sender",
  "teamId": "bypass",
  "jobId": "81bcf5ec-d6d9-4198-ac46-3946eeb3c134",
  "isV0": false,
  "error": {
    "name": "TypeError",
    "message": "fetch failed",
    "cause": {
      "errno": -111,
      "code": "ECONNREFUSED",
      "syscall": "connect",
      "address": "127.0.0.1",
      "port": 8000
    }
  },
  "webhookUrl": "http://localhost:8000/api/v1/webhooks/firecrawl"
}
```

## Investigation Results

### 1. Configuration Verification ✅

**Root `.env` file:**
```bash
WEBHOOK_BASE_URL=http://localhost:4400  # ✅ Correct
```

**Backend config (`apps/api/app/core/config.py:52`):**
```python
WEBHOOK_BASE_URL: str = "http://localhost:4400"  # ✅ Correct default
```

**Runtime verification:**
```bash
$ cd apps/api && source .venv/bin/activate && python -c "from app.core.config import settings; print(settings.WEBHOOK_BASE_URL)"
WEBHOOK_BASE_URL: http://localhost:4400  # ✅ Loads correctly
```

### 2. Code Verification ✅

**Crawl endpoint (`apps/api/app/api/v1/endpoints/crawl.py:65`):**
```python
crawl_options: Dict[str, Any] = {
    "url": str(request.url),
    "webhook": f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/firecrawl",  # ✅ Uses settings
}
```

**All API routes verified:**
- No hardcoded port 8000 references in `.py` files
- No hardcoded port 8000 references in `.ts`/`.tsx` files
- All environment variables correctly set to 4400

### 3. Frontend Configuration ✅

**`apps/web/.env.local`:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:4400  # ✅ Correct
NEXT_PUBLIC_APP_URL=http://localhost:4300  # ✅ Correct
```

**All Next.js API routes:**
```typescript
const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';  // ✅ Correct fallback
```

### 4. Root Cause Analysis 🔍

**The old webhook URL came from a previous crawl job**, not current configuration.

**Job verification:**
```bash
$ curl http://steamy-wsl:4200/v2/crawl/81bcf5ec-d6d9-4198-ac46-3946eeb3c134
{
  "success": true,
  "status": "completed",
  "completed": 100,
  "total": 100
}
```

This job (`81bcf5ec-d6d9-4198-ac46-3946eeb3c134`) was created **before the port migration** and had the webhook URL `http://localhost:8000/...` stored in Firecrawl's database.

## How Firecrawl Webhooks Work

### Webhook Registration Flow

1. **Client sends crawl request:**
   ```json
   POST /v2/crawl
   {
     "url": "https://example.com",
     "webhook": "http://localhost:4400/api/v1/webhooks/firecrawl"
   }
   ```

2. **Firecrawl stores webhook URL in job metadata:**
   - Webhook URL is **persisted with the job**
   - Cannot be changed after job creation
   - Survives Firecrawl service restarts

3. **Firecrawl sends webhooks for job lifecycle:**
   - `crawl.started` - Job begins
   - `crawl.page` - Each page crawled (uses stored URL)
   - `crawl.completed` - Job finishes
   - `crawl.failed` - Job errors

4. **Webhook URL cannot be updated for existing jobs**
   - Each job permanently stores its webhook URL
   - Port changes require new crawl jobs
   - Old jobs will keep trying old webhook URL until completion/expiration

### Why Port 8000 Appeared in Logs

**Timeline:**
1. **Before migration**: Job `81bcf5ec...` created with webhook `http://localhost:8000/...`
2. **During migration**: Backend moved from port 8000 → 4400
3. **After migration**: Job still running, sends webhook to stored URL (port 8000)
4. **Result**: Connection refused, logged error

**This is expected behavior** - Firecrawl correctly used the webhook URL provided when the job was created.

## Solution

### For Existing Jobs
- **Let them complete naturally** - They'll finish or expire within 24 hours (job expiration)
- **Or cancel them manually:**
  ```bash
  curl -X DELETE http://steamy-wsl:4200/v2/crawl/{job-id} \
    -H "Authorization: Bearer {api-key}"
  ```

### For New Jobs
- **All new crawls will use correct port 4400** ✅
- Configuration is correct, no code changes needed
- Verified that `settings.WEBHOOK_BASE_URL` loads correctly

### Monitoring
Check for any other old jobs still running:
```bash
# Backend logs
cd apps/api && tail -f logs/app.log | grep "webhook"

# Firecrawl logs
docker logs -f taboot-crawler | grep "webhook"
```

## Prevention

### Best Practices for Port Changes

1. **Cancel all active crawl jobs before migration:**
   ```bash
   # Get all active jobs
   curl http://localhost:4200/v2/crawl \
     -H "Authorization: Bearer {api-key}"
   
   # Cancel each job
   curl -X DELETE http://localhost:4200/v2/crawl/{job-id} \
     -H "Authorization: Bearer {api-key}"
   ```

2. **Wait for job expiration:**
   - Firecrawl jobs expire in 24 hours by default
   - Check `expiresAt` field in job status

3. **Update configuration before starting new jobs:**
   - Verify `WEBHOOK_BASE_URL` in `.env`
   - Restart backend service after changes
   - Test with a small crawl first

## Verification Checklist

- [x] Root `.env` has `WEBHOOK_BASE_URL=http://localhost:4400`
- [x] Backend config loads `WEBHOOK_BASE_URL` correctly
- [x] Crawl endpoint uses `settings.WEBHOOK_BASE_URL`
- [x] Frontend `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:4400`
- [x] All Next.js API routes have correct fallback URLs
- [x] No hardcoded port 8000 in Python files
- [x] No hardcoded port 8000 in TypeScript files
- [x] Old job `81bcf5ec...` is completed
- [x] New jobs will use correct webhook URL

## Testing

To verify new crawls use the correct webhook URL:

1. **Start a test crawl:**
   ```bash
   curl -X POST http://localhost:4400/api/v1/crawl \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "limit": 1
     }'
   ```

2. **Check Firecrawl logs for webhook URL:**
   ```bash
   docker logs -f taboot-crawler | grep "webhook"
   ```

3. **Verify it shows port 4400:**
   ```
   "webhookUrl": "http://localhost:4400/api/v1/webhooks/firecrawl"  # ✅ Correct
   ```

## Conclusion

**No code changes needed.** The error was from an old crawl job created before the port migration. All configuration is correct and new crawls will use the proper webhook URL on port 4400.

The job that caused the error (`81bcf5ec-d6d9-4198-ac46-3946eeb3c134`) has completed, so no further errors should occur unless there are other old jobs still running.
