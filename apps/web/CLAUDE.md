# GraphRAG Web - Frontend Guidelines

This file provides guidance to Claude Code when working with the Next.js frontend.

## Application Overview

The GraphRAG Web UI is a **NotebookLM-inspired conversational interface** built with:
- **Next.js 15** (App Router)
- **React 19** (Server + Client Components)
- **Tailwind CSS 4** (with shadcn/ui)
- **TypeScript 5** (strict mode)

The UI provides an AI-powered chat interface for querying crawled documentation with RAG (Retrieval-Augmented Generation).

## Architecture

### App Router Structure

```
app/
├── page.tsx                    # Main chat interface
├── layout.tsx                  # Root layout (fonts, theme)
├── globals.css                 # Tailwind base + custom styles
└── api/                        # Next.js API routes (backend proxy)
    └── crawl/
        ├── route.ts            # POST /api/crawl
        └── status/
            └── [jobId]/
                └── route.ts    # GET /api/crawl/status/:jobId

components/
├── chat/                       # Chat message components
│   ├── ChatHeader.tsx         # Header with title
│   ├── AIMessage.tsx          # Assistant message bubble
│   ├── UserMessage.tsx        # User message bubble
│   └── Citation.tsx           # Source citation badge
├── input/
│   └── ChatInput.tsx          # Message input + send button
├── layout/
│   ├── LeftSidebar.tsx        # Sources/spaces navigation
│   └── RightSidebar.tsx       # Context/settings panel
├── sidebar/                    # Sidebar sub-components
│   ├── SidebarHeader.tsx      # Logo + "Add Source" button
│   ├── SpacesSection.tsx      # Collapsible spaces list
│   ├── TagsSection.tsx        # Tag filters
│   └── StatisticsSection.tsx  # Crawl stats
├── workflows/
│   └── (...future workflow components)
└── ui/                         # shadcn/ui primitives
    ├── button.tsx
    ├── input.tsx
    ├── label.tsx
    ├── popover.tsx
    ├── switch.tsx
    └── tabs.tsx
```

### Component Architecture

**Design Pattern**: Composition over inheritance

- **Layout Components**: Structure (sidebars, headers)
- **Chat Components**: Message display with citations
- **Input Components**: User interaction (text input, buttons)
- **UI Components**: Radix primitives styled with Tailwind

**State Management**:
- React `useState` for local component state
- No global state library (yet) - keep it simple
- Server state fetched via Next.js API routes

## UI Design Philosophy

### NotebookLM-Inspired Interface

The UI mimics Google's NotebookLM with:
- **Three-column layout**: Sources (left) → Chat (center) → Context (right)
- **Clean typography**: Inter font, generous spacing
- **Subtle animations**: Fade-in, slide-up effects
- **Dark mode support**: System-aware theme switching

### Color System

Using Tailwind's zinc palette for neutral UI:
- Light mode: `zinc-50` (bg), `zinc-900` (text)
- Dark mode: `zinc-950` (bg), `zinc-50` (text)
- Accent: `blue-600` (links, citations)
- Borders: `zinc-200` / `zinc-800` (subtle)

**Custom scroll styling** (see `globals.css`):
```css
.custom-scroll::-webkit-scrollbar {
  width: 6px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: #a1a1aa; /* zinc-400 */
  border-radius: 3px;
}
```

## Critical Implementation Details

### Next.js API Routes as Proxy

**Why proxy?**  
Direct browser → FastAPI requests cause CORS issues. Next.js API routes run server-side and bypass CORS.

**Pattern**:
```typescript
// app/api/crawl/route.ts
export async function POST(request: Request) {
  const body = await request.json();
  
  const response = await fetch('http://localhost:8000/api/v1/crawl', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  
  const data = await response.json();
  return Response.json(data);
}
```

**Frontend calls**:
```typescript
// From client component
const response = await axios.post('/api/crawl', { url: 'https://...' });
```

### Component Patterns

#### Server Components (Default)

Use for static content and data fetching:
```typescript
// No "use client" directive
export default async function Page() {
  const data = await fetch('...');
  return <div>...</div>;
}
```

#### Client Components (Interactive)

Use for state, events, and browser APIs:
```typescript
"use client";

import { useState } from 'react';

export function ChatInput({ onSend }: Props) {
  const [message, setMessage] = useState('');
  
  const handleSubmit = () => {
    onSend(message);
    setMessage('');
  };
  
  return <input value={message} onChange={(e) => setMessage(e.target.value)} />;
}
```

**Rule**: Add `"use client"` only when needed (useState, useEffect, onClick, etc.)

### Type Safety

**No `any` types allowed** - use proper types or `unknown`:

```typescript
// ❌ Bad
const data: any = await response.json();

// ✅ Good
interface CrawlResponse {
  id: string;
  url: string;
}
const data: CrawlResponse = await response.json();

// ✅ Also good (unknown + type guard)
const data: unknown = await response.json();
if (typeof data === 'object' && data !== null && 'id' in data) {
  const crawlData = data as CrawlResponse;
}
```

**Axios Response Typing**:
```typescript
import axios, { AxiosResponse } from 'axios';

const response: AxiosResponse<CrawlResponse> = await axios.post('/api/crawl', body);
const { id, url } = response.data;
```

### Message Interface

```typescript
interface Message {
  id: string;                              // Unique ID (timestamp or UUID)
  role: 'user' | 'assistant';              // Message sender
  content: string | string[];              // Single or multi-paragraph
  citations?: Array<{                      // Source references
    number: number;                        // Citation index [1]
    title: string;                         // Source title
  }>;
  timestamp: string;                       // Display time (e.g., "2:34 PM")
}
```

**Multi-paragraph messages**:
```typescript
const message: Message = {
  id: '1',
  role: 'assistant',
  content: [
    'Based on your sources, GraphRAG uses Qdrant for vector storage.',
    'The embeddings are 768-dimensional from the TEI service.'
  ],
  citations: [{ number: 1, title: 'Architecture Docs' }],
  timestamp: '2:34 PM'
};
```

## Styling with Tailwind

### Responsive Design (Mobile-First)

**MANDATORY**: Design for mobile first, then scale up.

```typescript
// ❌ Bad (desktop-first)
<div className="w-72 sm:w-64">

// ✅ Good (mobile-first)
<div className="w-full sm:w-64 lg:w-72">
```

**Breakpoints**:
- `sm:` 640px (tablet portrait)
- `md:` 768px (tablet landscape)
- `lg:` 1024px (desktop)
- `xl:` 1280px (large desktop)
- `2xl:` 1536px (ultra-wide)

### Dark Mode

Use `dark:` variant for dark mode styles:
```typescript
<div className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-50">
```

**Theme switching** (future):
```typescript
// app/layout.tsx
<html className={theme === 'dark' ? 'dark' : ''}>
```

### shadcn/ui Components

Import from `@/components/ui`:
```typescript
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
```

**Custom styling**:
```typescript
<Button variant="outline" size="sm" className="gap-2">
  <Plus className="w-4 h-4" />
  Add Source
</Button>
```

**Variants** defined in component files using `class-variance-authority`.

## State Management Patterns

### Local State (useState)

For component-local data:
```typescript
const [messages, setMessages] = useState<Message[]>([]);
const [input, setInput] = useState('');
```

### Side Effects (useEffect)

For data fetching and subscriptions:
```typescript
useEffect(() => {
  const fetchStatus = async () => {
    const response = await axios.get(`/api/crawl/status/${jobId}`);
    setStatus(response.data);
  };
  
  const interval = setInterval(fetchStatus, 5000); // Poll every 5s
  return () => clearInterval(interval);
}, [jobId]);
```

**Dependency array rules**:
- Include all values used inside effect
- Use `[]` for mount-only effects
- Return cleanup function for subscriptions

### Props Drilling (Current Approach)

Pass props through component tree:
```typescript
<LeftSidebar onAddSource={handleAddSource} />
  <SidebarHeader onAddSource={onAddSource} />
    <Button onClick={onAddSource}>Add Source</Button>
```

**Future**: Consider Zustand or React Context for deep trees.

## API Integration

### Backend Communication

All backend calls go through Next.js API routes:

```typescript
// Start crawl
const response = await axios.post('/api/crawl', {
  url: 'https://docs.example.com',
  includePaths: ['docs/*'],
  maxDepth: 3,
});

// Get status
const status = await axios.get(`/api/crawl/status/${jobId}`);

// Query RAG
const results = await axios.post('/api/query', {
  query: 'How do I configure embeddings?',
  limit: 5,
  use_llm: true,
});
```

### Error Handling

**Never fail silently** - show errors to user:

```typescript
try {
  const response = await axios.post('/api/crawl', body);
  // Handle success
} catch (error) {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail || 'Request failed';
    alert(message); // TODO: Replace with toast notification
  } else {
    throw error; // Re-throw unexpected errors
  }
}
```

**Future**: Replace `alert()` with toast component (e.g., `sonner`).

## Development Workflow

### Running the Dev Server

```bash
# From apps/web:
npm run dev

# Or from repo root:
npm run dev:web
```

Server runs on `http://localhost:3000`.

### Testing Philosophy (TDD Required)

**RED-GREEN-REFACTOR** (not yet implemented):

1. **RED**: Write failing test
   ```typescript
   // __tests__/ChatInput.test.tsx
   test('calls onSend when user submits message', () => {
     const onSend = jest.fn();
     render(<ChatInput onSend={onSend} />);
     
     fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hello' } });
     fireEvent.click(screen.getByRole('button'));
     
     expect(onSend).toHaveBeenCalledWith('Hello');
   });
   ```

2. **GREEN**: Implement component
3. **REFACTOR**: Clean up

**Test Structure** (future):
```
__tests__/
├── components/
│   ├── ChatInput.test.tsx
│   ├── AIMessage.test.tsx
│   └── LeftSidebar.test.tsx
├── api/
│   └── crawl.test.ts
└── pages/
    └── page.test.tsx
```

### Code Quality

```bash
# Lint
npm run lint

# Type check
npx tsc --noEmit

# Build
npm run build
```

**ESLint** configured with Next.js rules + TypeScript.

## Common Development Tasks

### Adding a New Component

1. **Write test** in `__tests__/components/`
2. **Create component file** in `components/<category>/`
3. **Define props interface**:
   ```typescript
   interface MyComponentProps {
     title: string;
     onAction: () => void;
   }
   ```
4. **Implement component** (server or client)
5. **Export from index** if needed

### Adding a New API Route

1. **Create route file** in `app/api/<path>/route.ts`
2. **Implement handler**:
   ```typescript
   export async function GET(request: Request) {
     const response = await fetch(`${process.env.API_URL}/endpoint`);
     const data = await response.json();
     return Response.json(data);
   }
   ```
3. **Add TypeScript types** for request/response

### Modifying the Message UI

1. **Update `Message` interface** in relevant file
2. **Modify `AIMessage.tsx` or `UserMessage.tsx`**
3. **Update parent component** (`page.tsx`) to pass new props

### Adding a New Sidebar Section

1. **Create component** in `components/sidebar/`
2. **Import in `LeftSidebar.tsx` or `RightSidebar.tsx`**
3. **Add collapsible logic** if needed (see existing sections)

## Dependencies

```json
{
  "dependencies": {
    "next": "16.0.1",                      // Framework
    "react": "19.2.0",                     // UI library
    "react-dom": "19.2.0",
    "axios": "^1.13.1",                    // HTTP client
    "@radix-ui/react-*": "...",            // UI primitives
    "tailwindcss": "^4",                   // Styling
    "class-variance-authority": "^0.7.1",  // Component variants
    "tailwind-merge": "^3.3.1",            // Class merging
    "tailwindcss-animate": "^1.0.7"        // Animations
  }
}
```

## Known Issues

### CORS with Direct API Calls

**Problem**: Browser blocks `localhost:3000` → `localhost:8000` requests.  
**Solution**: Always use Next.js API routes as proxy.

### State Persistence

**Current**: Messages lost on page refresh.  
**Future**: Add localStorage or backend session storage.

### Real-time Updates

**Current**: 5-second polling for crawl status.  
**Future**: Consider WebSocket or Server-Sent Events for live updates.

### Mobile Sidebar Toggle

**Current**: Sidebars always visible on desktop.  
**Future**: Add hamburger menu for mobile, collapsible sidebars.

## Pre-Production Notes

Per root CLAUDE.md: **Breaking changes are acceptable.**

- Refactor components freely
- No backward compatibility required
- Prioritize type safety and code clarity
- Focus on mobile-first design

## Resources

- **Next.js 15 Docs**: https://nextjs.org/docs
- **React 19 Docs**: https://react.dev
- **Tailwind CSS**: https://tailwindcss.com
- **shadcn/ui**: https://ui.shadcn.com
- **Radix UI**: https://www.radix-ui.com
