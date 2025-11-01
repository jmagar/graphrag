# Crawl Defaults Configuration

**Date**: January 10, 2025  
**Change**: Made crawl defaults configurable via environment variables  
**Status**: ✅ **COMPLETE**

---

## Summary

✅ **Default max depth**: Changed from hardcoded `2` → configurable (default `3`)  
✅ **Default max pages**: Changed from hardcoded `10` → configurable (default `100`)  
✅ **Max limits**: Made configurable (depth limit: `10`, pages limit: `1000`)  
✅ **All values**: Now driven by environment variables (not hardcoded)

---

## New Environment Variables

### Frontend Configuration

**File**: `apps/web/.env.local`

```env
# Crawl Configuration
NEXT_PUBLIC_CRAWL_MAX_DEPTH=3           # Default: 3 levels deep
NEXT_PUBLIC_CRAWL_MAX_PAGES=100         # Default: 100 pages
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=10    # Max allowed: 10 levels
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=1000  # Max allowed: 1000 pages
```

---

## How It Works

### Before (Hardcoded) ❌

```typescript
// Old code
{
  max_depth: z.number().default(2).describe("Maximum crawl depth (1-5)"),
  max_pages: z.number().default(10).describe("Maximum number of pages (1-100)")
}

// Processing
maxDiscoveryDepth: Math.min(Math.max(args.max_depth, 1), 5),
limit: Math.min(Math.max(args.max_pages, 1), 100)
```

**Problems**:
- ❌ Hardcoded default of 2 (too shallow for most sites)
- ❌ Hardcoded limits of 5 and 100 (not flexible)
- ❌ Requires code changes to adjust defaults

---

### After (Configurable) ✅

```typescript
// New code - loads from env vars
const DEFAULT_MAX_DEPTH = parseInt(process.env.NEXT_PUBLIC_CRAWL_MAX_DEPTH || "3", 10);
const DEFAULT_MAX_PAGES = parseInt(process.env.NEXT_PUBLIC_CRAWL_MAX_PAGES || "100", 10);
const MAX_DEPTH_LIMIT = parseInt(process.env.NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT || "10", 10);
const MAX_PAGES_LIMIT = parseInt(process.env.NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT || "1000", 10);

// Tool schema
{
  max_depth: z.number().default(DEFAULT_MAX_DEPTH)
    .describe(`Maximum crawl depth (1-${MAX_DEPTH_LIMIT})`),
  max_pages: z.number().default(DEFAULT_MAX_PAGES)
    .describe(`Maximum number of pages (1-${MAX_PAGES_LIMIT})`)
}

// Processing
maxDiscoveryDepth: Math.min(Math.max(args.max_depth, 1), MAX_DEPTH_LIMIT),
limit: Math.min(Math.max(args.max_pages, 1), MAX_PAGES_LIMIT)
```

**Benefits**:
- ✅ Defaults configurable via `.env.local`
- ✅ Limits configurable per environment
- ✅ No code changes needed to adjust
- ✅ Can have different settings for dev/staging/prod

---

## Configuration Examples

### Example 1: Default (Balanced)

```env
NEXT_PUBLIC_CRAWL_MAX_DEPTH=3
NEXT_PUBLIC_CRAWL_MAX_PAGES=100
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=10
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=1000
```

**Use case**: General documentation sites  
**Result**: Crawls 3 levels deep, up to 100 pages

---

### Example 2: Shallow & Fast

```env
NEXT_PUBLIC_CRAWL_MAX_DEPTH=2
NEXT_PUBLIC_CRAWL_MAX_PAGES=50
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=5
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=200
```

**Use case**: Quick testing, small sites  
**Result**: Crawls 2 levels deep, up to 50 pages

---

### Example 3: Deep Indexing

```env
NEXT_PUBLIC_CRAWL_MAX_DEPTH=5
NEXT_PUBLIC_CRAWL_MAX_PAGES=500
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=20
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=5000
```

**Use case**: Large documentation sites, wikis  
**Result**: Crawls 5 levels deep, up to 500 pages

---

### Example 4: Production (Conservative)

```env
NEXT_PUBLIC_CRAWL_MAX_DEPTH=3
NEXT_PUBLIC_CRAWL_MAX_PAGES=100
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=5
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=500
```

**Use case**: Production environment with cost controls  
**Result**: Default 3/100, max 5/500 (prevents runaway crawls)

---

## User Experience

### Scenario 1: User Says "Crawl docs.claude.com"

**Without specifying parameters**:
```
AI uses defaults:
- max_depth: 3 (from NEXT_PUBLIC_CRAWL_MAX_DEPTH)
- max_pages: 100 (from NEXT_PUBLIC_CRAWL_MAX_PAGES)

Result: Crawls up to 3 levels, stops at 100 pages
```

---

### Scenario 2: User Says "Crawl docs.claude.com with depth 5"

**User specifies depth**:
```
AI uses:
- max_depth: 5 (user-specified, clamped to MAX_DEPTH_LIMIT=10)
- max_pages: 100 (default)

Result: Crawls up to 5 levels, stops at 100 pages
```

---

### Scenario 3: User Says "Index entire site up to 1000 pages"

**User specifies pages**:
```
AI uses:
- max_depth: 3 (default)
- max_pages: 1000 (user-specified, clamped to MAX_PAGES_LIMIT=1000)

Result: Crawls up to 3 levels, stops at 1000 pages
```

---

### Scenario 4: User Tries to Exceed Limits

**User says "Crawl with depth 50 and 10000 pages"**:
```
AI requests:
- max_depth: 50
- max_pages: 10000

Code clamps to limits:
- max_depth: min(50, 10) = 10 (MAX_DEPTH_LIMIT)
- max_pages: min(10000, 1000) = 1000 (MAX_PAGES_LIMIT)

Result: Crawls up to 10 levels, stops at 1000 pages
```

---

## Variable Reference

| Variable | Purpose | Default | Range |
|----------|---------|---------|-------|
| `NEXT_PUBLIC_CRAWL_MAX_DEPTH` | Default crawl depth | `3` | 1+ |
| `NEXT_PUBLIC_CRAWL_MAX_PAGES` | Default max pages | `100` | 1+ |
| `NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT` | Maximum allowed depth | `10` | 1+ |
| `NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT` | Maximum allowed pages | `1000` | 1+ |

---

## Validation & Bounds

```typescript
// Depth is clamped between 1 and MAX_DEPTH_LIMIT
maxDiscoveryDepth: Math.min(Math.max(args.max_depth, 1), MAX_DEPTH_LIMIT)
//                          ^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^
//                          Min: 1 (at least 1 level)  Max: configurable

// Pages is clamped between 1 and MAX_PAGES_LIMIT
limit: Math.min(Math.max(args.max_pages, 1), MAX_PAGES_LIMIT)
//              ^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^
//              Min: 1 (at least 1 page)  Max: configurable
```

**This prevents**:
- ❌ Zero or negative depths
- ❌ Zero or negative page counts
- ❌ Runaway crawls that exceed system limits

---

## Environment-Specific Configs

### Development (`.env.local`)

```env
# Fast iteration, limited scope
NEXT_PUBLIC_CRAWL_MAX_DEPTH=2
NEXT_PUBLIC_CRAWL_MAX_PAGES=20
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=5
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=100
```

### Staging (`.env.staging`)

```env
# Similar to production, but higher limits for testing
NEXT_PUBLIC_CRAWL_MAX_DEPTH=3
NEXT_PUBLIC_CRAWL_MAX_PAGES=200
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=10
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=2000
```

### Production (`.env.production`)

```env
# Conservative defaults, reasonable limits
NEXT_PUBLIC_CRAWL_MAX_DEPTH=3
NEXT_PUBLIC_CRAWL_MAX_PAGES=100
NEXT_PUBLIC_CRAWL_MAX_DEPTH_LIMIT=5
NEXT_PUBLIC_CRAWL_MAX_PAGES_LIMIT=500
```

---

## Testing the Changes

### 1. Verify Environment Variables Load

```bash
cd apps/web
npm run dev
```

Check console for:
```
Using crawl defaults: depth=3, pages=100, limits: depth=10, pages=1000
```

### 2. Test Default Crawl

In chat UI:
```
crawl https://example.com
```

**Expected**: Uses depth=3, pages=100

### 3. Test User Override

In chat UI:
```
crawl https://example.com with depth 5 and 200 pages
```

**Expected**: Uses depth=5, pages=200 (within limits)

### 4. Test Limit Clamping

In chat UI:
```
crawl https://example.com with depth 50
```

**Expected**: Clamped to depth=10 (MAX_DEPTH_LIMIT)

---

## Migration Guide

### If You Previously Had Custom Defaults

**Old approach** (editing code):
```typescript
// Had to edit firecrawl-tools.ts
max_depth: z.number().default(5).describe("..."),
```

**New approach** (edit .env):
```env
# Just update .env.local
NEXT_PUBLIC_CRAWL_MAX_DEPTH=5
```

**Migration steps**:
1. Note your current hardcoded values
2. Add them to `.env.local`
3. Restart web app
4. Verify with a test crawl

---

## Files Modified

1. ✅ `apps/web/lib/firecrawl-tools.ts`
   - Added environment variable reading
   - Made defaults and limits configurable
   - Updated descriptions to show dynamic limits

2. ✅ `apps/web/.env.local`
   - Added crawl configuration variables

3. ✅ `apps/web/.env.example`
   - Documented new variables

4. ✅ `.env.example` (root)
   - Documented new variables for reference

---

## Restart Required

**The web app must be restarted** for env variable changes to take effect:

```bash
# In terminal running web app
Ctrl+C

# Restart
cd apps/web
npm run dev
```

**Note**: Next.js loads `NEXT_PUBLIC_*` variables at **build time**, so any changes require a restart.

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Default depth | 2 (hardcoded) | 3 (configurable) |
| Default pages | 10 (hardcoded) | 100 (configurable) |
| Max depth limit | 5 (hardcoded) | 10 (configurable) |
| Max pages limit | 100 (hardcoded) | 1000 (configurable) |
| Change defaults | Edit code | Edit .env |
| Per-environment | Impossible | Easy |
| Testing | Requires code changes | Requires env changes |

---

## Summary

✅ **Crawl defaults now configurable via environment variables**  
✅ **Default max depth**: 3 (was 2)  
✅ **Default max pages**: 100 (was 10)  
✅ **Limits**: Configurable per environment  
✅ **No hardcoded values**: All driven by env vars  

**Ready to use** - restart web app and test! 🚀
