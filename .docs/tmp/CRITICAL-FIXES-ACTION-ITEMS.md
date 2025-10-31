# Critical Fixes Required - Action Items
**Status:** 🔴 BLOCKING PRODUCTION DEPLOYMENT  
**Estimated Time:** 15 minutes  
**Effort Level:** EASY

---

## ❌ FIX #1: Type Safety Violation (5 min)

**File:** `apps/web/components/chat/Artifact.tsx`  
**Line:** 49

**REPLACE THIS:**
```typescript
code({ className, children, ...props }: any) {
```

**WITH THIS:**
```typescript
code({ className, children, ...props }: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement>) {
```

**Why:** TypeScript strict mode violation. Removes implicit `any` type.

---

## ❌ FIX #2: Enable Tailwind Typography Plugin (2 min)

**File:** `tailwind.config.ts`

**ADD AT TOP:**
```typescript
import typography from '@tailwindcss/typography';
```

**CHANGE THIS:**
```typescript
plugins: [tailwindcssAnimate],
```

**TO THIS:**
```typescript
plugins: [typography, tailwindcssAnimate],
```

**Why:** Markdown prose classes require this plugin. Currently broken.  
**Proof:** Run `npm run build` - you'll see prose classes not compiling.

---

## ❌ FIX #3: Correct CodeBlock Import Path (2 min)

**File:** `apps/web/components/chat/Artifact.tsx`  
**Line:** 15

**REPLACE THIS:**
```typescript
import { CodeBlock, CodeBlockCode } from './CodeBlock';
```

**WITH THIS:**
```typescript
import { CodeBlock, CodeBlockCode } from '@/components/ui/code-block';
```

**Then DELETE:** `apps/web/components/chat/CodeBlock.tsx` (duplicate file)

**Why:** Uses centralized component instead of duplicate.

---

## ❌ FIX #4: Delete Deprecated Files (2 min)

**Delete these files:**
1. `apps/web/components/chat/Citation.tsx.deprecated`
2. `apps/web/components/chat/ToolCall.tsx.deprecated`
3. `apps/web/components/chat/TypingIndicator.tsx.deprecated`

**Why:** No longer used, migrated to prompt-kit versions.

---

## Verification Checklist

After making all fixes, run:

```bash
# Check TypeScript compilation
npm run build

# Check types specifically
cd apps/web && npx tsc --noEmit

# Check for any remaining 'any' types in chat components
grep -r " any" apps/web/components/chat/
```

**Expected Result:**
- ✅ Build completes without errors
- ✅ No TypeScript errors
- ✅ No `any` type found in grep results

---

## Impact Summary

| Issue | Impact | Fix Time | Blocker |
|-------|--------|----------|---------|
| `any` type in Artifact | Type safety violation | 5 min | YES |
| Missing typography plugin | Markdown broken | 2 min | YES |
| Wrong CodeBlock import | Duplicated code | 2 min | YES |
| Deprecated files | Code cleanliness | 2 min | NO |

**Total Time:** 15 minutes  
**Total Blockers:** 3 critical  
**Action:** DO NOW before deploying

---

## Files Involved

```
apps/web/
├── components/
│   ├── chat/
│   │   ├── Artifact.tsx          ← FIX #1, #2, #3
│   │   ├── CodeBlock.tsx         ← DELETE
│   │   ├── Citation.tsx.deprecated ← DELETE
│   │   ├── ToolCall.tsx.deprecated ← DELETE
│   │   └── TypingIndicator.tsx.deprecated ← DELETE
│   └── ui/
│       └── code-block.tsx        ← Source of truth for CodeBlock
└── tailwind.config.ts            ← FIX #2
```

---

## Rollback Plan

If something breaks after these fixes:

```bash
# Revert the type change
git checkout apps/web/components/chat/Artifact.tsx

# Revert tailwind config
git checkout tailwind.config.ts

# Restore the deleted CodeBlock duplicate
git checkout apps/web/components/chat/CodeBlock.tsx
```

---

## Questions?

Check the full audit report: `prompt-kit-migration-complete-audit.md`

For code review: All changes are minimal, mechanical updates (no logic changes).

---

**Prepared by:** Research Agent Audit  
**Date:** 2025-10-30  
**Status:** Ready for implementation
