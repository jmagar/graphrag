# Tool Display Implementation

## Overview
Implemented real-time tool call visualization in the GraphRAG chat interface to show when the AI assistant is using tools like web scraping, crawling, and search.

## Changes Made

### 1. Enhanced Stream Event Handling (page.tsx)
**Location:** `apps/web/app/page.tsx`

- Added tool call tracking using Map to accumulate tool use events
- Captures `content_block_start` events when tool use begins
- Captures `input_json_delta` events to show tool parameters in real-time
- Updates UI immediately when tools are invoked

**Key Implementation:**
```typescript
const toolsInUse = new Map<string, { name: string; input: string }>();

// Tool use started
if (event?.type === 'content_block_start' && event.content_block?.type === 'tool_use') {
  const toolId = event.content_block.id;
  const toolName = event.content_block.name;
  toolsInUse.set(toolId, { name: toolName, input: '' });
  // Update UI...
}
```

### 2. Enhanced ToolCall Component
**Location:** `apps/web/components/chat/ToolCall.tsx`

**Features:**
- Color-coded by tool category (blue for scraping, purple for crawling, green for search, etc.)
- Displays tool name with MCP prefix removed for cleaner UX
- Shows status icon (spinning loader, checkmark, or error X)
- Expandable to show full parameters
- Mobile-responsive design

**Tool Categories:**
- `scrape_url` - Blue with document icon
- `start_crawl` / `check_crawl_status` - Purple with globe icon
- `search_web` / `query_knowledge_base` - Green with search icon
- `map_website` - Yellow with map icon
- `extract_structured_data` - Orange with database icon

### 3. Tools Documentation Component
**Location:** `apps/web/components/tools/ToolsInfo.tsx`

**Features:**
- Lists all 7 available Firecrawl/GraphRAG tools
- Categorized by: Web Scraping, Website Crawling, Search
- Shows tool description and parameters
- Indicates required vs optional parameters
- Expandable cards for detailed parameter info
- Category filtering

**Available Tools Documented:**
1. `scrape_url` - Get content from a single webpage
2. `map_website` - List all URLs on a site
3. `search_web` - Search the web with full content
4. `extract_structured_data` - Extract specific data fields
5. `start_crawl` - Index entire website into Qdrant
6. `check_crawl_status` - Monitor crawl progress
7. `query_knowledge_base` - Semantic search of indexed content

### 4. Right Sidebar Enhancement
**Location:** `apps/web/components/layout/RightSidebar.tsx`

- Added tabbed interface: "Workflows" and "Tools"
- Tools tab displays the ToolsInfo component
- Maintains existing workflow cards
- Mobile-responsive tabs

## User Benefits

### Real-Time Feedback
- Users can now see when the AI is using tools
- Shows which specific tool is being invoked
- Displays tool parameters as they stream in
- Visual status indicators (running/complete/error)

### Tool Discovery
- Users can browse available tools in the sidebar
- Understand what capabilities the AI has
- Learn tool parameters and usage
- Filter tools by category

### Better UX
- Reduced confusion about what AI is doing
- Transparency in AI operations
- Educational - users learn about available tools
- Mobile-friendly expandable design

## Technical Details

### Stream Event Processing
The implementation correctly handles Claude Agent SDK's `stream_event` messages:
- `content_block_start` with `type: 'tool_use'` → Tool invocation begins
- `content_block_delta` with `type: 'input_json_delta'` → Parameters streaming
- `content_block_delta` with `type: 'text_delta'` → Text response streaming

### State Management
- Tool calls stored in message state
- Real-time updates without re-rendering entire message
- Accumulated JSON parsing for parameter display

### Mobile Optimization
- Collapsible tool parameter sections
- Touch-friendly expandable cards
- Responsive color schemes
- Proper text wrapping and truncation

## Future Enhancements

### Possible Improvements:
1. Add tool result display (not just invocation)
2. Show tool execution time
3. Add tool usage analytics
4. Tool favoriting/recent tools
5. Copy tool parameters for manual execution
6. Search/filter tools in documentation
7. Add tool examples/templates

## Testing Checklist

- [ ] Ask AI to scrape a URL - verify tool call displays
- [ ] Ask AI to search the web - verify streaming parameters
- [ ] Start a crawl - verify crawl tool shows with status
- [ ] Check mobile display of tool calls
- [ ] Verify Tools tab in sidebar shows all 7 tools
- [ ] Test category filtering in tools documentation
- [ ] Expand tool cards to see parameters
- [ ] Verify color coding of different tool types

## Notes

- Claude Agent SDK automatically manages tool permissions via `permissionMode: 'bypassPermissions'`
- Tool names are prefixed with `mcp__firecrawl-tools__` - component strips this for display
- All tools are defined in `/apps/web/lib/firecrawl-tools.ts` using SDK MCP server
- Backend proxy endpoints remain unchanged - all tool execution happens through SDK
