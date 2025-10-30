# Tool Call Badge Enhancements & Map Endpoint Fix

## Overview
Enhanced the visual design of tool call badges and fixed the `/map` endpoint bug.

---

## 1. Fixed `/map` Endpoint Bug

**Issue**: Firecrawl v2 returns links as objects `[{"url": "..."}]`, but backend expected strings.

**File**: `apps/api/app/api/v1/endpoints/map.py:47-48`

```python
# Extract URL strings from link objects
links = result.get("links", [])
urls = [link["url"] if isinstance(link, dict) else link for link in links]
```

**Testing**:
```bash
curl 'http://localhost:4400/api/v1/map/' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://docs.claude.com","limit":10}'

# Returns: {"success":true,"urls":["https://...", ...], "total":10}
```

**Frontend**: Added missing `toolCalls` prop to `/map` response
- File: `apps/web/app/page.tsx:343-346`

---

## 2. Enhanced Tool Call Badge Design

**File**: `apps/web/components/chat/ToolCall.tsx`

### Visual Improvements

**Multi-layer Gradients** (line 82):
```tsx
bg-gradient-to-br from-white via-zinc-50 to-zinc-100/80
dark:from-zinc-800/80 dark:via-zinc-850/60 dark:to-zinc-900/80
backdrop-blur-xl
```

**Refined Shadows**:
```tsx
shadow-lg shadow-zinc-200/50 dark:shadow-zinc-900/50
hover:shadow-xl hover:shadow-zinc-300/60 dark:hover:shadow-zinc-900/70
```

**Animated Icon Container** (lines 88-93):
- Gradient background: `from-blue-500/10 via-purple-500/10 to-pink-500/10`
- Hover effects: `group-hover:scale-110 group-hover:rotate-6`
- Inner glow layer on hover

**Gradient Text** (lines 96-98):
```tsx
text-transparent bg-clip-text
bg-gradient-to-r from-zinc-800 to-zinc-600
dark:from-zinc-100 dark:to-zinc-300
```

**Status Indicators** (lines 69-86):
- **Running**: Pulsing gradient orb with ping animation
- **Complete**: Checkmark in emerald gradient circle
- **Error**: X mark in red gradient circle

**Interactions**:
```tsx
hover:scale-[1.02] active:scale-[0.98]
transition-all duration-300
```

---

## 3. ReactMarkdown Implementation (Earlier)

**File**: `apps/web/components/chat/AIMessage.tsx:72-106`

Replaced `dangerouslySetInnerHTML` with `ReactMarkdown`:
- Added `remarkGfm` plugin for GitHub Flavored Markdown
- Custom component overrides for headings, lists, links, code
- Dark mode styling for all markdown elements
- Consistent with `Artifact.tsx` prose styles

---

## Files Changed

1. `apps/api/app/api/v1/endpoints/map.py` - Fixed link extraction
2. `apps/web/app/page.tsx` - Added toolCalls to /map response
3. `apps/web/components/chat/ToolCall.tsx` - Enhanced badge design
4. `apps/web/components/chat/AIMessage.tsx` - ReactMarkdown implementation (earlier)

---

## Testing

```bash
# Map endpoint works
curl 'http://localhost:4400/api/v1/map/' -d '{"url":"https://docs.claude.com","limit":10}'

# Frontend: Try /map command to see new badges
/map https://docs.claude.com
```
