# Claude Agent SDK Integration - Implementation Summary

## Project: GraphRAG Chat Interface Enhancement

**Date:** 2025-10-30  
**Branch:** `feat/graphrag-ui-interface`  
**PR:** #2 - https://github.com/jmagar/graphrag/pull/2

---

## Key Implementation Details

### 1. Claude Agent SDK Integration
**Critical:** Uses **Claude Agent SDK** (NOT the regular Anthropic SDK)

**File:** `apps/web/app/api/chat/route.ts`
- Imports: `import { query } from "@anthropic-ai/claude-agent-sdk"`
- Spawns local Claude Code CLI process (no API calls to Anthropic)
- Simple string prompts work: `query({ prompt: message, options: {...} })`
- Streams via Server-Sent Events (SSE)
- Uses `bypassPermissions` mode for seamless chat
- Custom system prompt for GraphRAG context

**Package:** `@anthropic-ai/claude-agent-sdk` (installed in `apps/web`)

### 2. Automatic URL Scraping

**Detection:** `apps/web/app/page.tsx` (lines 45-47)
```typescript
const urlRegex = /^https?:\/\/.+$/i;
const isUrl = urlRegex.test(content.trim());
```

**Scrape Flow:**
1. Frontend: `apps/web/app/api/scrape/route.ts` → Proxy to backend
2. Backend: `apps/api/app/api/v1/endpoints/scrape.py` → Calls Firecrawl
3. Service: `apps/api/app/services/firecrawl.py::scrape_url()` → Already existed
4. Router: `apps/api/app/api/v1/router.py` → Added scrape router

**Response:** Returns markdown in artifact format with metadata

### 3. Artifact System

**File:** `apps/web/components/chat/Artifact.tsx`

**Key Fixes Applied:**
- **Dark Mode Fix:** Force white background, explicit text colors
  - Background: `bg-white dark:bg-zinc-900`
  - Text: `text-zinc-900` for headings, `text-zinc-800` for paragraphs
- **Image Removal:** `img: () => null` in ReactMarkdown components
- **Syntax Highlighting:** Prism with vscDarkPlus theme
- **Copy Functionality:** One-click copy with visual feedback

**Supported Types:** markdown, code, json, html, text

### 4. Chat UX Improvements

**Keyboard Shortcuts** - `apps/web/components/input/ChatInput.tsx` (lines 80-84)
```typescript
// Changed from: if (e.key === 'Enter' && (e.metaKey || e.ctrlKey))
// To:
if (e.key === 'Enter' && !e.shiftKey) {
  e.preventDefault();
  handleSend();
}
```
- **Enter** sends message
- **Shift+Enter** adds new line

**Typing Indicator** - `apps/web/components/chat/TypingIndicator.tsx` (new file)
- Animated bouncing dots
- Shows when `isLoading` is true
- Rendered in `apps/web/app/page.tsx` after messages

**Rate Limiting** - `apps/web/app/page.tsx` (lines 29-43)
- Max 5 messages per minute
- Uses `useRef` to track timestamps across renders
- Alert shown when limit exceeded

### 5. Duplicate Message Fix

**Problem:** Both `assistant` and `stream_event` messages were processed

**Solution:** `apps/web/app/page.tsx` (lines 191-203)
```typescript
// ONLY process stream_event for live updates
if (parsed.type === 'stream_event') {
  const event = parsed.event;
  if (event?.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
    accumulatedContent += event.delta.text;
    // Update message
  }
}
```

Removed the `assistant` message handler completely.

---

## Dependencies Added

**Frontend (`apps/web/package.json`):**
- `@anthropic-ai/claude-agent-sdk` - Claude Agent SDK
- `react-markdown` - Markdown rendering
- `remark-gfm` - GitHub Flavored Markdown
- `react-syntax-highlighter` - Code syntax highlighting
- `@types/react-syntax-highlighter` - TypeScript types
- `zod@3` - Schema validation

---

## File Changes Summary

### Backend Files
- `apps/api/app/api/v1/endpoints/scrape.py` - **NEW** - Scrape endpoint
- `apps/api/app/api/v1/router.py` - Added scrape router import/registration
- `apps/api/app/services/firecrawl.py` - Already had `scrape_url()` method

### Frontend Files
- `apps/web/app/api/chat/route.ts` - **NEW** - Claude Agent SDK integration
- `apps/web/app/api/scrape/route.ts` - **NEW** - Scrape API proxy
- `apps/web/app/page.tsx` - URL detection, message handling, scraped context
- `apps/web/components/chat/Artifact.tsx` - **NEW** - Rich content renderer
- `apps/web/components/chat/TypingIndicator.tsx` - **NEW** - Loading indicator
- `apps/web/components/chat/AIMessage.tsx` - Added artifact prop support
- `apps/web/components/input/ChatInput.tsx` - Keyboard shortcuts fix

---

## Configuration Notes

**No API Key Required:** Claude Agent SDK uses local Claude Code CLI
- Requires: `claude` binary in PATH (`which claude` → `/home/jmagar/.nvm/versions/node/v22.19.0/bin/claude`)
- No `ANTHROPIC_API_KEY` environment variable needed
- Uses `bypassPermissions` mode for auto-approval

**Environment Files:**
- `.env.example` - Added `ANTHROPIC_API_KEY` placeholder (for documentation)
- `apps/web/.env.local` - Template created (not actually needed for SDK)

---

## Testing Completed

✅ Enter sends messages (Shift+Enter for new line)  
✅ URL auto-scraping works (tested with GitHub URLs)  
✅ Artifacts display with proper colors (white bg, dark text)  
✅ No images/emojis appear in scraped content  
✅ Claude can see scraped content for follow-up questions  
✅ Typing indicator shows when loading  
✅ Rate limiting enforced (5 messages/minute)  
✅ No duplicate messages  
✅ Mobile responsive design  

---

## Git History

```
79c8108 - chore: sync external changes to chat components
25235ef - fix: improve chat UX with keyboard shortcuts, artifact display, and typing indicator
4100c6f - feat: add artifact system for rich content rendering
ac0d4f2 - feat: add automatic URL scraping in chat
246315c - fix: prevent duplicate assistant messages and add rate limiting
ddc4089 - feat: integrate Claude Agent SDK for chat functionality
d751ba1 - feat: implement pixel-perfect GraphRAG UI (baseline for PR)
```

**Base Branch:** `main` (reset to `d751ba1`)  
**Feature Branch:** `feat/graphrag-ui-interface`  
**PR:** #2 with 6 commits

---

## Critical Learnings

1. **Claude Agent SDK ≠ Anthropic SDK**
   - Must use `@anthropic-ai/claude-agent-sdk` package
   - Spawns local CLI, doesn't call APIs
   - Requires `claude` binary installed

2. **Message Type Handling**
   - SDK emits both `assistant` and `stream_event` messages
   - Only process `stream_event` to avoid duplicates
   - Look for `content_block_delta` with `text_delta` type

3. **Artifact Dark Mode**
   - Don't rely on `prose-invert` utility classes
   - Explicitly set text colors: `text-zinc-900`, `text-zinc-800`
   - Force backgrounds: `bg-white dark:bg-zinc-900`
   - Remove images: `img: () => null` in ReactMarkdown

4. **Scraped Content Context**
   - Store in message metadata: `metadata.scrapedContent`
   - Include in next message to Claude: `[Previously scraped from URL]:\n{content}`
   - Filter from history to avoid duplication

---

## End Result

✅ Fully functional chat powered by Claude Agent SDK  
✅ Beautiful artifact rendering with proper colors  
✅ Auto URL scraping with Firecrawl integration  
✅ Professional chat UX (typing indicator, shortcuts, rate limiting)  
✅ Mobile responsive  
✅ Ready for production use
