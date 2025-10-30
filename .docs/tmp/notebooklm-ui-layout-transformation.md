# NotebookLM UI Layout Transformation

## Date
2025-10-30

## Objective
Reorganize the NotebookLM-style interface to add Tags section, condense Sources/Statistics, and replace right sidebar with Workflows panel.

## Changes Made

### File Modified
- `/home/jmagar/code/graphrag/notebooklm-final.html`

### Left Sidebar Reorganization

**Previous Structure:**
1. Conversation Tabs (top)
2. Conversations List (full height)

**New Structure (Top → Bottom):**
1. **Tags Section** (NEW)
   - Word cloud with variable-sized pills
   - Colors: blue, emerald, purple, amber, cyan, rose, indigo, teal
   - Text sizes: `text-xs`, `text-sm`, `text-[11px]`, `text-[10px]`
   - Tags: embeddings, qdrant, vector-search, api, configuration, crawling, dimensions, tei
   - Location: Lines 115-128

2. **Sources** (Condensed)
   - Reduced from separate section to compact list
   - 24px icons with truncated names
   - 3 visible items: Getting Started, API Docs, Blog Posts
   - "View all" link added
   - Location: Lines 130-162

3. **Statistics** (Compact)
   - Key-value pairs format
   - Documents: 1,247 | Vectors: 45.2K | Storage: 2.4 GB
   - Location: Lines 164-181

4. **Conversations** (Bottom)
   - Tabs: All | Recent | ⭐ (condensed)
   - Smaller conversation cards
   - Reduced padding: `p-2` instead of `p-3`
   - Smaller text: `text-xs`, `text-[11px]`, `text-[10px]`
   - Location: Lines 183-206

### Right Sidebar - Workflows (NEW)

**Added:** Lines 370-480

**7 Workflow Cards:**
1. **Create** (blue) - Generate new content
2. **Report** (emerald) - Build comprehensive report
3. **Mind Map** (purple) - Visualize connections
4. **Graph** (cyan) - Explore knowledge graph
5. **Plan** (amber) - Create project plan
6. **PRD** (rose) - Product requirements doc
7. **Tasks** (indigo) - Break down into tasks

**Card Structure:**
- `w-full p-4 rounded-xl border-2`
- Color-coded borders on hover: `hover:border-[color]-500`
- Icon with colored background: `bg-[color]-500/10`
- Title + description layout
- Hover effects: border color + background tint

### Design Details

**Tags Section:**
- Variable sizing creates word cloud effect
- Hover states: `hover:bg-[color]-100 dark:hover:bg-[color]-500/20`
- Cursor pointer for interactivity

**Workflow Cards:**
- 40px icons with rounded-lg backgrounds
- Group hover transitions: `group-hover:bg-[color]-500/20`
- Consistent spacing: `gap-3`, `mb-0.5`
- Dark mode support throughout

## Result
- Left sidebar now has 4 distinct sections with Tags at top
- Right sidebar provides action-oriented workflows
- More condensed, information-dense layout
- Better visual hierarchy with color coding
- All existing features (@ mentions, reactions, timestamps) preserved

## Access
http://localhost:8080/notebooklm-final.html
