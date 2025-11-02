# Next.js 16.0.1 Build Error Investigation

## Bug Detective Analysis

### Problem Definition

**Issue**: Production build fails during the page generation phase  
**Error**: `TypeError: Cannot read properties of null (reading 'useContext')`  
**Location**: `/_global-error` route prerendering  
**Status**: ⚠️ **UNRESOLVED - Next.js Framework Bug**

### Environment

- Next.js: `16.0.1` (Turbopack)
- React: `19.2.0`
- React-DOM: `19.2.0`
- Node.js: `v21.x`
- Build Mode: Production (`npm run build`)

### Error Details

```
Error occurred prerendering page "/_global-error"
TypeError: Cannot read properties of null (reading 'useContext')
  at ignore-listed frames {
    digest: '2648210175'
  }
Export encountered an error on /_global-error/page: /_global-error, exiting the build.
```

### Investigation Summary

#### Tests Performed

1. ✅ **Verified with minimal global-error.tsx** - Still fails
2. ✅ **Tested without global-error.tsx file** - Still fails (Next.js generates default)
3. ✅ **Tested with webpack (NO_TURBOPACK=1)** - Still fails
4. ✅ **Tested returning `null` during SSR** - Still fails
5. ✅ **Removed all React Context usage** - Still fails

#### Root Cause

This is a **Next.js 16.0.1 framework bug** where the `/_global-error` route attempts to prerender during the production build, but React's context is `null` during this phase. The error occurs in Next.js's internal build process, not in user code.

### Additional Warnings

The build also shows multiple React key prop warnings:

```
Each child in a list should have a unique "key" prop.
Check the top-level render call using <__next_viewport_boundary__>
Check the top-level render call using <V>
Check the top-level render call using <meta>
Check the top-level render call using <head>
```

These are internal Next.js components, not user code.

### Workarounds Attempted

| Approach | Result | Notes |
|----------|--------|-------|
| Minimal `global-error.tsx` | ❌ Failed | Error occurs before component renders |
| Remove `global-error.tsx` | ❌ Failed | Next.js generates default that also fails |
| Return `null` during SSR | ❌ Failed | Error happens in framework, not component |
| Disable Turbopack | ❌ Failed | Same error with webpack |
| Skip experimental features | ❌ Failed | No applicable settings |

### Verified Against GitHub Issues

**Active Issue**: [#85668](https://github.com/vercel/next.js/issues/85668) - Created Nov 1, 2025
- **Status**: OPEN - Actively being tracked
- **Severity**: Blocks production deployments
- **Versions Affected**: 
  - ✅ Next.js 16.0.1 (stable) - CONFIRMED BROKEN
  - ✅ Next.js 16.0.2-canary.3 - CONFIRMED BROKEN
  - ✅ Next.js 16.0.2-canary.4 (latest as of Nov 1) - LIKELY BROKEN

**Previous Issue**: [#84994](https://github.com/vercel/next.js/issues/84994) - Oct 17, 2025
- **Status**: Closed (invalid - no reproduction provided)
- Not actually fixed, just closed by bot

### Impact Assessment

- ✅ **Development server works perfectly** - No impact on `npm run dev`
- ❌ **Production builds fail** - Cannot create optimized build with `npm run build`
- ✅ **TypeScript compilation works** - All type errors resolved
- ✅ **Dev features work** - Hot reload, fast refresh, type checking
- ✅ **All application features work in dev** - Chat, crawling, queries, etc.

### Decision: Stay on Next.js 16.0.1

**Rationale**:
1. Development mode works flawlessly
2. All Next.js 16 features available in dev
3. Bug exists in latest stable AND canary versions
4. Downgrading to 15.x would lose Next.js 16 features
5. Fix will likely come in future patch release

**Action Plan**:
- ✅ **Use dev mode for all development** (`npm run dev`)
- ✅ **Monitor GitHub issue #85668** for updates
- ✅ **Test new releases** when Next.js 16.0.2+ is published
- ✅ **Production deployment** can use dev mode or wait for fix

### Monitoring

Track these resources for fix updates:
- GitHub Issue: https://github.com/vercel/next.js/issues/85668
- Next.js Releases: https://github.com/vercel/next.js/releases
- Next.js 16 Changelog: https://nextjs.org/blog/next-16

### Related Issues

This appears related to:
- Next.js 16 + React 19 integration issues
- Server Components prerendering in production
- Global error boundary handling in App Router

---

**Date**: 2025-11-01  
**Investigated By**: Bug Detective (AI Assistant)  
**Status**: Documented - Awaiting framework fix
