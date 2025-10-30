# Session-Based Conversation Context - FINAL IMPLEMENTATION

## ✅ Correct Approach: SDK Session Management

After reading the Claude Agent SDK documentation more carefully, the **correct approach** is to use **session-based conversation management**, not manual history tracking.

### How It Works

1. **First Message**: Call `query()` without session ID
2. **SDK Returns**: `session_id` in the `system.init` message
3. **Frontend Captures**: Store `session_id` in state
4. **Subsequent Messages**: Call `query({ prompt: message, options: { resume: sessionId } })`
5. **SDK Manages**: All conversation state server-side

### Key Insight

The SDK is **stateful** - it maintains conversation history on the server side. You don't send history with each request - you just provide a session ID to resume!

```typescript
// ❌ WRONG - Manual history tracking
query({
  prompt: buildHistoryString(conversationHistory),
  options: { /* ... */ }
})

// ✅ CORRECT - Session-based resumption
query({
  prompt: currentMessage,
  options: {
    resume: sessionId  // SDK loads history automatically
  }
})
```

---

## Implementation

### Backend: `apps/web/app/api/chat/route.ts`

```typescript
interface ChatRequest {
  message: string;
  sessionId?: string; // For resuming existing conversation
}

export async function POST(request: NextRequest) {
  const { message, sessionId } = await request.json();

  const stream = new ReadableStream({
    async start(controller) {
      const agentQuery = query({
        prompt: message, // Just current message
        options: {
          ...(sessionId && { resume: sessionId }), // Resume if exists
          maxTurns: 10,
          includePartialMessages: true,
          permissionMode: "bypassPermissions",
          mcpServers: { "firecrawl-tools": firecrawlServer },
          allowedTools: [/* all tools */],
          systemPrompt: "..."
        }
      });

      for await (const msg of agentQuery) {
        // Capture and send session ID from init message
        if (msg.type === 'system' && msg.subtype === 'init') {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({
            type: 'session_init',
            session_id: msg.session_id
          })}\\n\\n`));
        }
        
        // Stream all other messages
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(msg)}\\n\\n`));
        
        if (msg.type === "result") {
          controller.enqueue(encoder.encode("data: [DONE]\\n\\n"));
          break;
        }
      }
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive"
    }
  });
}
```

### Frontend: `apps/web/app/page.tsx`

```typescript
export default function GraphRAGPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const handleSendMessage = async (content: string) => {
    // ... user message creation ...

    // Send with session ID
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ 
        message: content,
        sessionId  // Resume existing session
      })
    });

    const reader = response.body?.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') break;

          const parsed = JSON.parse(data);

          // CAPTURE SESSION ID
          if (parsed.type === 'session_init') {
            setSessionId(parsed.session_id);
            console.log('Session started:', parsed.session_id);
          }

          // Handle streaming content
          if (parsed.type === 'stream_event') {
            // ... update message content ...
          }
        }
      }
    }
  };
}
```

---

## Message Flow

### First Message
```
User → Frontend → Backend → SDK query()
                              ↓
                        system.init message
                              ↓
                        session_id: "abc123"
                              ↓
Frontend captures → setSessionId("abc123")
```

### Subsequent Messages
```
User → Frontend (has sessionId: "abc123")
         ↓
     Backend query({ 
       prompt: "What did you just tell me?",
       options: { resume: "abc123" }
     })
         ↓
     SDK loads conversation history
         ↓
     Claude responds with context
```

---

## Benefits

✅ **Automatic Context**: SDK handles conversation state  
✅ **No Manual History**: Don't build/send history arrays  
✅ **Efficient**: Only send current message  
✅ **Persistent**: Sessions survive across SDK calls  
✅ **Fork Support**: Can branch conversations with `forkSession: true`  
✅ **MCP Tools Work**: Tools have access to full conversation  

---

## Session Lifecycle

### New Conversation
```typescript
// No sessionId = new conversation
const response = await fetch('/api/chat', {
  body: JSON.stringify({ message: "Hello!" })
});
// SDK creates new session, returns session_id
```

### Continue Conversation
```typescript
// With sessionId = resume conversation
const response = await fetch('/api/chat', {
  body: JSON.stringify({ 
    message: "Tell me more",
    sessionId: "abc123" // Resume
  })
});
// SDK loads previous context
```

### Fork Conversation
```typescript
// Future: Branch conversation
const response = await fetch('/api/chat', {
  body: JSON.stringify({ 
    message: "Let's try a different approach",
    sessionId: "abc123",
    forkSession: true // Creates new session from this point
  })
});
// SDK creates new session_id with history up to fork point
```

---

## Comparison: Manual vs Session-Based

### ❌ Manual History (Old Approach)
```typescript
// Frontend builds history
const history = messages.map(m => ({
  role: m.role,
  content: m.content
}));

// Send everything every time
fetch('/api/chat', {
  body: JSON.stringify({ message, history })
});

// Backend reconstructs context
const fullPrompt = history.map(h => 
  `${h.role}: ${h.content}`
).join('\\n\\n') + `\\n\\nUser: ${message}`;

query({ prompt: fullPrompt });
```

**Problems:**
- Manual tracking
- Large payloads
- Complex string building
- Fragile edge cases
- Scraped content management headaches

### ✅ Session-Based (Correct Approach)
```typescript
// Frontend just has session ID
const sessionId = "abc123";

// Send only current message
fetch('/api/chat', {
  body: JSON.stringify({ message, sessionId })
});

// Backend just resumes
query({ 
  prompt: message,
  options: { resume: sessionId }
});
```

**Benefits:**
- Simple & clean
- Minimal payloads
- SDK manages state
- Robust & reliable
- Tool context automatic

---

## Future: Persistent Sessions

For persistence across page reloads, add:

### IndexedDB Storage
```typescript
// Save session to IndexedDB
const saveSession = async (sessionId: string) => {
  await db.sessions.put({
    id: sessionId,
    createdAt: Date.now(),
    lastMessageAt: Date.now()
  });
};

// Load on mount
useEffect(() => {
  const loadSession = async () => {
    const latestSession = await db.sessions.orderBy('lastMessageAt').last();
    if (latestSession) {
      setSessionId(latestSession.id);
    }
  };
  loadSession();
}, []);
```

### Session List UI
```typescript
// Show all sessions
const sessions = await db.sessions.toArray();

// Resume any session
const handleResumeSession = (id: string) => {
  setSessionId(id);
  // Next message automatically resumes this session
};

// Fork session
const handleForkSession = (id: string) => {
  // Send with forkSession: true
  // Creates new session_id from fork point
};
```

---

## Testing

### Test Conversation Memory
```
1. User: "My name is Alice"
   Claude: "Nice to meet you, Alice!"

2. User: "What's my name?"
   Claude: "Your name is Alice."  ✅ Has context

3. User: "Can you scrape react.dev?"
   Claude: [uses scrape_url tool] ✅ Tool works

4. User: "What did that page say about hooks?"
   Claude: "Based on the React documentation I scraped, hooks are..."
   ✅ Remembers previous tool results
```

### Test Session Resumption
```typescript
// Get session ID from first message
console.log('Session:', sessionId); // "abc123"

// Reload page (sessionId lost in current impl)
// Future: Load from IndexedDB

// Resume with sessionId
// SDK loads full conversation history
```

---

## Summary

**The Claude Agent SDK uses session-based state management:**

1. ✅ Call `query()` → Get `session_id`
2. ✅ Store `session_id` in frontend state
3. ✅ Resume with `{ resume: sessionId }`
4. ✅ SDK handles all conversation history
5. ✅ MCP tools have full context
6. ✅ No manual history tracking needed

**This is the official, supported way to maintain conversation context with the SDK.**
