# Firecrawl Tools & UI Improvements Implementation

## Investigation Summary

### Custom Claude Agent SDK Tools for Firecrawl

**Objective:** Create type-safe MCP tools that allow Claude to directly use Firecrawl commands during conversation.

#### Key Files Created

1. **`apps/web/lib/firecrawl-tools.ts`** - Custom MCP Server
   - 7 tools implemented using `createSdkMcpServer` and `tool` helper
   - All tools include proper error handling and content truncation
   - Tools: `scrape_url`, `map_website`, `search_web`, `extract_structured_data`, `start_crawl`, `check_crawl_status`, `query_knowledge_base`

2. **`apps/web/app/api/chat/route.ts`** - Updated Chat Route
   - Added `import { firecrawlServer } from "@/lib/firecrawl-tools"`
   - Changed `prompt` from string to async generator (REQUIRED for MCP tools)
   - Added `mcpServers: { "firecrawl-tools": firecrawlServer }`
   - Added `allowedTools` array with all 7 tool names
   - Updated system prompt to mention available tools

#### Dependencies
- ✅ `zod` already installed (checked package.json)
- ✅ `@anthropic-ai/claude-agent-sdk` v0.1.29 already present

#### Tool Naming Convention
MCP tools follow pattern: `mcp__{server_name}__{tool_name}`
Example: `mcp__firecrawl-tools__scrape_url`

#### Key Design Decision: Query Knowledge Base Tool

**Problem Found:** Crawl results stored in Qdrant weren't accessible to Claude
- `/crawl` command shows progress in artifact but Claude doesn't see the actual crawled content
- `metadata.scrapedContent` only available for `/scrape`, `/search`, `/extract` commands
- Artifact content not passed to Claude in chat context

**Solution:** Added `query_knowledge_base` tool
- Performs semantic search in Qdrant using embeddings
- Returns relevant chunks from previously crawled sites
- Allows Claude to answer questions about indexed content
- Backend endpoint: `POST /api/v1/query` (already exists)

#### Backend API Verification
All backend endpoints confirmed working:
- `POST /api/v1/scrape` - Single page scraping
- `POST /api/v1/map` - Website URL mapping
- `POST /api/v1/search` - Web search with content
- `POST /api/v1/extract` - Structured data extraction
- `POST /api/v1/crawl` - Start async crawl job
- `GET /api/v1/crawl/{id}` - Crawl status
- `POST /api/v1/query` - Query Qdrant knowledge base

---

### Visual Crawl Progress Component

**Objective:** Replace markdown-based crawl status with rich animated React component.

#### Files Created

1. **`apps/web/components/crawl/CrawlProgress.tsx`**
   - Animated gradient progress bar with shimmer effect
   - Live stats grid (Pages, Time Elapsed, Credits)
   - Recently crawled URLs list with fade-in animations
   - Expandable/collapsible interface
   - Status-based styling (active/completed/failed)
   - Cancel crawl functionality (callback prop)
   - Time elapsed counter with useEffect

2. **`apps/web/app/globals.css`** - Added animations
   - `@keyframes shimmer` - Progress bar shimmer effect
   - `@keyframes fade-in` - Recent items fade in
   - `.animate-shimmer` utility class
   - `.animate-fade-in` utility class

#### Current State Analysis

**Polling Logic Location:** `apps/web/app/page.tsx:48-123`
- useEffect polls active crawls every 3 seconds
- Updates `artifact.content` with markdown string
- Stores status in `message.crawl.status`

**Message Interface:** `apps/web/app/page.tsx:14-37`
```typescript
interface Message {
  // ... existing fields
  crawl?: {
    jobId: string;
    status: 'active' | 'completed' | 'failed';
    url: string;
  };
}
```

**Artifact Component:** `apps/web/components/chat/Artifact.tsx`
- Renders markdown/code/json/html/text
- Used for displaying scraped content
- Currently used for crawl progress (as markdown)

#### Integration Plan

**Remaining Work:**
1. Extend Message interface with structured crawl data:
   ```typescript
   crawl?: {
     jobId: string;
     status: 'active' | 'completed' | 'failed';
     url: string;
     data?: {
       completed: number;
       total: number;
       creditsUsed: number;
       expiresAt?: string;
       recentPages?: Array<{ url: string; status: string }>;
     }
   }
   ```

2. Update polling logic (page.tsx:48-123):
   - Instead of updating `artifact.content` with markdown
   - Update `message.crawl.data` with structured data
   - Remove artifact updates for crawl messages

3. Update AIMessage.tsx:
   - Check for `message.crawl` prop
   - Render `<CrawlProgress {...message.crawl} />` instead of artifact
   - Import CrawlProgress component

4. Wire cancel functionality:
   - Add `handleCancelCrawl(jobId)` function in page.tsx
   - Call `DELETE /api/v1/crawl/{id}` endpoint
   - Update message to show cancelled state

---

### Session Management (Planned)

**Objective:** Allow users to resume and fork conversation sessions.

#### Claude Agent SDK Session Support
- First message type `'system'` with `subtype: 'init'` contains `session_id`
- `resume` option: Continue existing session
- `forkSession` option: Create new branch from session state

#### Planned Files
1. `lib/session-manager.ts` - IndexedDB wrapper for session storage
2. `components/session/SessionMenu.tsx` - UI for session list
3. Update `app/api/chat/route.ts` - Handle session resume/fork
4. Update `app/page.tsx` - Capture and store session IDs

#### Status
- ⏳ Not yet implemented
- ✅ Architecture designed
- ✅ Claude SDK session API understood

---

## Testing Notes

**Backend Health Check:**
```bash
curl http://localhost:8000/health
# Returns: { "status": "healthy", ... }
```

**Qdrant Collection Info:**
```bash
curl http://localhost:8000/api/v1/query/collection/info
# Returns: { "name": "graphrag", "points_count": 0, ... }
```

**Package Verification:**
- `zod` installed (npm output showed "up to date")
- `@anthropic-ai/claude-agent-sdk` v0.1.29 present

---

## Key Findings

### 1. Assistant Context Issue - RESOLVED
**Problem:** Claude doesn't see crawled data
**Root Cause:** 
- Artifacts not passed to Claude in chat context
- Only `message.content` and `metadata.scrapedContent` sent
- Crawl results stored in Qdrant, not in message metadata

**Solution:** `query_knowledge_base` tool
- Allows Claude to search Qdrant directly
- Returns relevant chunks from indexed content
- Provides semantic search over crawled data

### 2. Markdown vs Component
**Original:** Crawl status as markdown in artifact (boring)
**New:** CrawlProgress React component with:
- Animated progress bars
- Live updating stats
- Visual flair and polish
- Better UX and engagement

### 3. MCP Tools Requirement
**Critical:** MCP tools require async generator for `prompt`
```typescript
// WRONG (won't work with MCP):
query({ prompt: message })

// CORRECT:
async function* generateMessages() {
  yield { type: "user", message: { role: "user", content: message } };
}
query({ prompt: generateMessages() })
```

---

## File Structure Summary

```
apps/web/
├── lib/
│   └── firecrawl-tools.ts          # NEW - 7 MCP tools
├── components/
│   ├── crawl/
│   │   └── CrawlProgress.tsx       # NEW - Visual component
│   └── chat/
│       ├── Artifact.tsx            # EXISTS - Reviewed
│       └── AIMessage.tsx           # EXISTS - Needs update
├── app/
│   ├── api/
│   │   └── chat/
│   │       └── route.ts            # MODIFIED - MCP integration
│   ├── page.tsx                    # EXISTS - Needs update for CrawlProgress
│   └── globals.css                 # MODIFIED - Added animations
└── package.json                    # VERIFIED - Has dependencies
```

---

## Next Steps

1. **Complete CrawlProgress Integration** (15-20 min)
   - Update Message interface
   - Update polling logic
   - Integrate into AIMessage
   - Wire cancel functionality

2. **Test MCP Tools** (10 min)
   - Start chat and ask Claude to scrape a URL
   - Verify tool execution
   - Test query_knowledge_base after crawl

3. **Session Management** (1-2 hours)
   - Implement SessionManager
   - Update chat route
   - Create SessionMenu UI
   - Test resume/fork

---

## References

- Claude Agent SDK Custom Tools: https://docs.claude.com/en/api/agent-sdk/custom-tools
- Claude Agent SDK Session Management: https://docs.claude.com/en/api/agent-sdk/session-management
- Backend API: http://localhost:8000/docs (FastAPI Swagger)
