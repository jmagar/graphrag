# Typing Indicator Double Avatar Fix

## Problem
Double avatars were showing in the chat interface when the assistant was responding - one from `AIMessage` component and one from `TypingIndicator` component.

## Investigation

### Initial Issue Location
**File**: `apps/web/app/page.tsx:780`
```typescript
{isLoading && <TypingIndicator />}
```

**Root Cause**:
- Assistant message created immediately with `isStreaming: true` at line 550-560
- `AIMessage` component rendered with its avatar at line 760-769
- `TypingIndicator` also rendered with its own avatar at line 780
- Result: Two avatars displayed simultaneously

### Component Structure Analysis

**TypingIndicator** (`apps/web/components/chat/TypingIndicator.tsx:10`):
- Renders its own AI avatar
- Shows "Thinking..." text with animated dots
- Completely separate from AIMessage

**AIMessage** (`apps/web/components/chat/AIMessage.tsx:48-49`):
- Renders AI avatar in `flex-shrink-0` container
- Displays message content
- No logic for streaming state

## Solution

### Approach
Instead of showing a separate `TypingIndicator` component, integrate the typing indicator into `AIMessage` itself when streaming with no content.

### Changes Made

#### 1. AIMessage Component (`apps/web/components/chat/AIMessage.tsx`)

**Added `isStreaming` prop** (line 14):
```typescript
interface AIMessageProps {
  isStreaming?: boolean;
  // ... other props
}
```

**Added typing indicator logic** (lines 47-49):
```typescript
const hasNoContent = content.length === 0 || (content.length === 1 && content[0] === '');
const showTypingIndicator = isStreaming && hasNoContent && (!toolCalls || toolCalls.length === 0);
```

**Conditional rendering** (lines 70-80):
```typescript
{showTypingIndicator ? (
  <div className="flex items-center gap-2">
    <span className="text-sm text-zinc-500 dark:text-zinc-400">Thinking</span>
    <div className="flex gap-1">
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  </div>
) : (
  // ... regular content rendering
)}
```

#### 2. Page Component (`apps/web/app/page.tsx`)

**Passed `isStreaming` prop** (line 765):
```typescript
<AIMessage
  isStreaming={message.isStreaming}
  // ... other props
/>
```

**Kept fallback TypingIndicator** (line 780):
```typescript
{isLoading && !messages.some(m => m.isStreaming) && <TypingIndicator />}
```
- Only shows when loading but no streaming message exists
- Handles edge cases where message hasn't been created yet

## Result

### Flow
1. User sends message → `isLoading = true`
2. Assistant message created with `isStreaming: true`, empty content
3. AIMessage renders with **one avatar** + typing indicator
4. Content streams in → typing indicator replaced by markdown
5. Stream completes → `isStreaming = false`

### Key Improvements
- ✅ Single avatar displayed at all times
- ✅ Typing indicator integrated into message flow
- ✅ Smooth transition from typing to content
- ✅ No visual jump or layout shift
- ✅ Maintains animation consistency

## Files Modified
- `apps/web/components/chat/AIMessage.tsx` (lines 14, 47-49, 70-80, 125)
- `apps/web/app/page.tsx` (line 765)
