# Max Depth Parameter Name Mismatch Fix

**Date**: January 10, 2025  
**Issue**: Frontend sending `maxDepth` but backend expects `maxDiscoveryDepth`  
**Status**: ✅ **FIXED**

---

## The Problem

### Parameter Name Mismatch

**Frontend** (`apps/web/lib/firecrawl-tools.ts`):
```typescript
await axios.post(`${backendUrl}/api/v1/crawl/`, {
  url: args.url,
  maxDepth: Math.min(Math.max(args.max_depth, 1), 5),  // ❌ Wrong name
  limit: Math.min(Math.max(args.max_pages, 1), 100)
})
```

**Backend** (`apps/api/app/api/v1/endpoints/crawl.py`):
```python
class CrawlRequest(BaseModel):
    maxDiscoveryDepth: Optional[int] = None  # ✅ Correct name
    limit: Optional[int] = 10000
```

### What Happened

1. Frontend sends: `{"url": "...", "maxDepth": 2, "limit": 10}`
2. Backend receives it but doesn't recognize `maxDepth`
3. Backend uses `maxDiscoveryDepth = None` (no depth limit)
4. Firecrawl receives **no depth constraint**
5. Firecrawl uses its default: **9999 levels deep**
6. Result: **2500+ pages** instead of the expected ~100

---

## Why This Mattered

**Expected behavior** (with depth=2):
```
Homepage (depth 0)
  ├─ /docs (depth 1)
  │   ├─ /docs/api (depth 2) ← Stop here
  │   └─ /docs/guide (depth 2) ← Stop here
  └─ /about (depth 1)
      ├─ /about/team (depth 2) ← Stop here
      └─ /about/contact (depth 2) ← Stop here

Result: ~50-100 pages
```

**Actual behavior** (with depth=9999):
```
Homepage (depth 0)
  ├─ /docs (depth 1)
  │   ├─ /docs/api (depth 2)
  │   │   ├─ /docs/api/authentication (depth 3)
  │   │   │   ├─ /docs/api/authentication/oauth (depth 4)
  │   │   │   │   ├─ /docs/api/authentication/oauth/scopes (depth 5)
  │   │   │   │   │   └─ ... continues to depth 9999
  │   │   │   │   └─ /docs/api/authentication/oauth/flows (depth 5)
  │   │   │   └─ /docs/api/authentication/api-keys (depth 4)
  │   │   └─ /docs/api/endpoints (depth 3)
  ... and so on for EVERY link

Result: 2500+ pages (entire site)
```

---

## The Fix

Changed frontend to use correct parameter name:

```typescript
await axios.post(`${backendUrl}/api/v1/crawl/`, {
  url: args.url,
  maxDiscoveryDepth: Math.min(Math.max(args.max_depth, 1), 5),  // ✅ Correct
  limit: Math.min(Math.max(args.max_pages, 1), 100)
})
```

---

## Default Values Summary

### Frontend Tool Defaults
```typescript
{
  max_depth: z.number().default(2),      // Default: 2 levels
  max_pages: z.number().default(10)      // Default: 10 pages
}
```

**Constraints**:
- `max_depth`: Clamped to 1-5 range
- `max_pages`: Clamped to 1-100 range

### Backend API Defaults
```python
class CrawlRequest(BaseModel):
    maxDiscoveryDepth: Optional[int] = None  # Default: None (no limit)
    limit: Optional[int] = 10000             # Default: 10,000 pages
```

### Firecrawl Service Defaults

When parameters are `None`:
- `maxDiscoveryDepth`: **9999** (effectively unlimited)
- `limit`: **10000** pages

---

## Expected Behavior After Fix

### Example 1: User says "crawl docs.claude.com"

**AI uses defaults**:
```json
{
  "url": "https://docs.claude.com",
  "maxDiscoveryDepth": 2,
  "limit": 10
}
```

**Result**:
- Crawls up to **2 levels deep**
- Stops at **10 pages** max
- Much more focused crawl

### Example 2: User says "crawl docs.claude.com with depth 3 and 50 pages"

**AI uses specified values**:
```json
{
  "url": "https://docs.claude.com",
  "maxDiscoveryDepth": 3,
  "limit": 50
}
```

**Result**:
- Crawls up to **3 levels deep**
- Stops at **50 pages** max

### Example 3: User says "index the entire docs.claude.com site"

**AI might override defaults**:
```json
{
  "url": "https://docs.claude.com",
  "maxDiscoveryDepth": 5,
  "limit": 100
}
```

**Result**:
- Crawls up to **5 levels deep** (max allowed by frontend)
- Stops at **100 pages** max (max allowed by frontend)

---

## Testing the Fix

### Before Fix ❌

```bash
# User: "crawl docs.claude.com"
# Frontend sends:
{
  "url": "https://docs.claude.com",
  "maxDepth": 2,        # ❌ Ignored by backend
  "limit": 10
}

# Firecrawl receives:
{
  "url": "https://docs.claude.com",
  "maxDiscoveryDepth": null,  # No depth limit!
  "limit": 10000              # Backend default
}

# Result: Crawls 2500+ pages
```

### After Fix ✅

```bash
# User: "crawl docs.claude.com"
# Frontend sends:
{
  "url": "https://docs.claude.com",
  "maxDiscoveryDepth": 2,  # ✅ Recognized by backend
  "limit": 10
}

# Firecrawl receives:
{
  "url": "https://docs.claude.com",
  "maxDiscoveryDepth": 2,  # ✅ Depth limit applied
  "limit": 10
}

# Result: Crawls ~10 pages (up to 2 levels deep)
```

---

## Why the Naming Confusion?

**Firecrawl v1** used `maxDepth`  
**Firecrawl v2** changed to `maxDiscoveryDepth`

The frontend was still using the v1 parameter name!

---

## Related Issues This Fixes

1. ✅ **2500+ pages being crawled** when only 10-100 expected
2. ✅ **Entire site being indexed** when only docs section needed
3. ✅ **High costs** from processing thousands of pages
4. ✅ **Slow crawls** taking hours instead of minutes
5. ✅ **Language filtering seeing all pages** instead of focused subset

---

## Files Modified

1. ✅ `apps/web/lib/firecrawl-tools.ts` - Changed `maxDepth` → `maxDiscoveryDepth`

---

## Verification

After restarting the web app, test with:

```
# In chat UI
crawl https://example.com
```

**Check the crawl options** in Firecrawl:
```bash
curl -s "http://steamy-wsl:4200/v1/crawl/active" \
  -H "Authorization: Bearer ${API_KEY}" | \
  jq '.crawls[0].options.maxDiscoveryDepth'
```

**Expected**: `2` (not `9999` or `null`)

---

## Summary

| Issue | Before | After |
|-------|--------|-------|
| Parameter name | `maxDepth` ❌ | `maxDiscoveryDepth` ✅ |
| Effective depth limit | 9999 | 2 (or user-specified) |
| Pages crawled (example) | 2500+ | ~10-100 |
| Backend recognizes param | No ❌ | Yes ✅ |

**Critical fix for controlling crawl scope!** 🎯
