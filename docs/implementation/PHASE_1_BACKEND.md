# Phase 1: Backend Integration

**Status**: 🔵 Not Started (Blocked by Phase 0)  
**Duration**: 2 weeks (Weeks 3-4)  
**Priority**: High  
**Prerequisites**: Phase 0 complete (✅)

---

## 🎯 Objectives

Connect the production-ready chat UI to the RAG backend, add conversation persistence, and establish real-time data flow between frontend and backend.

### Success Criteria
- ✅ Conversations persist across page refreshes
- ✅ Message history loads correctly
- ✅ Chat uses RAG system (not Claude SDK directly)
- ✅ @mentions show real sources from Qdrant
- ✅ All features work with backend APIs
- ✅ Tests maintain 80%+ coverage

---

## 📋 Deliverables

### 1. Conversation Persistence (Database)
**Goal**: Store conversations and messages permanently

#### Database Schema (SQLite/PostgreSQL)
```sql
-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    space VARCHAR(50) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(255),  -- For future multi-user support
    metadata JSONB DEFAULT '{}'
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    sources JSONB DEFAULT '[]'  -- Store RAG sources
);

-- Conversation tags (many-to-many)
CREATE TABLE conversation_tags (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,
    PRIMARY KEY (conversation_id, tag)
);

-- Indexes
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_conversations_space ON conversations(space);
CREATE INDEX idx_conversation_tags_tag ON conversation_tags(tag);
```

#### Backend Implementation
```python
# apps/api/app/db/models.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    space = Column(String(50), default="default")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String(255), nullable=True)
    metadata = Column(JSONB, default={})
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    tags = relationship("ConversationTag", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSONB, default={})
    sources = Column(JSONB, default=[])
    
    conversation = relationship("Conversation", back_populates="messages")

class ConversationTag(Base):
    __tablename__ = "conversation_tags"
    
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), primary_key=True)
    tag = Column(String(50), primary_key=True)
    
    conversation = relationship("Conversation", back_populates="tags")
```

#### Database Service
```python
# apps/api/app/services/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session
```

---

### 2. Conversation API Endpoints
**Goal**: CRUD operations for conversations and messages

#### Pydantic Models
```python
# apps/api/app/api/v1/endpoints/conversations.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class MessageCreate(BaseModel):
    role: str
    content: str
    metadata: Optional[dict] = {}

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime
    metadata: dict
    sources: List[dict]

class ConversationCreate(BaseModel):
    title: str
    space: Optional[str] = "default"
    initial_message: Optional[MessageCreate] = None

class ConversationResponse(BaseModel):
    id: UUID
    title: str
    space: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    message_count: int
    last_message_preview: Optional[str]

class ConversationDetail(ConversationResponse):
    messages: List[MessageResponse]
```

#### Endpoints
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database import get_session

router = APIRouter()

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_session)
):
    """Create a new conversation."""
    # Implementation with TDD tests
    pass

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    space: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session)
):
    """List conversations with filters."""
    pass

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session)
):
    """Get conversation with all messages."""
    pass

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_session)
):
    """Update conversation metadata."""
    pass

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session)
):
    """Delete a conversation."""
    pass

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: UUID,
    message: MessageCreate,
    db: AsyncSession = Depends(get_session)
):
    """Add a message to conversation."""
    pass
```

---

### 3. RAG Integration in Chat
**Goal**: Replace Claude SDK with backend RAG system

#### Chat Endpoint with RAG
```python
# apps/api/app/api/v1/endpoints/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
from app.services.llm import LLMService

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    conversation_id: Optional[UUID] = None
    message: str
    use_rag: bool = True
    sources: Optional[List[str]] = None  # @mentions
    limit: int = 5

class ChatResponse(BaseModel):
    message: MessageResponse
    sources: List[dict]
    conversation_id: UUID

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Chat with RAG system.
    
    Flow:
    1. Generate embedding for user message
    2. Search vector DB for relevant context
    3. Build prompt with context
    4. Generate LLM response
    5. Store user message and assistant response
    6. Return response with sources
    """
    embeddings_service = EmbeddingsService()
    vector_db_service = VectorDBService()
    llm_service = LLMService()
    
    # 1. Search for relevant context (if RAG enabled)
    sources = []
    context = ""
    if request.use_rag:
        query_embedding = await embeddings_service.generate_embedding(request.message)
        search_results = await vector_db_service.search(
            query_embedding=query_embedding,
            limit=request.limit,
            filters=_build_filters(request.sources)
        )
        sources = search_results
        context = _format_context(search_results)
    
    # 2. Generate LLM response
    llm_response = await llm_service.generate_response(
        query=request.message,
        context=context
    )
    
    # 3. Store messages in database
    conversation_id = request.conversation_id or await _create_conversation(db, request.message)
    
    # Save user message
    user_message = await _save_message(
        db, conversation_id, "user", request.message
    )
    
    # Save assistant message with sources
    assistant_message = await _save_message(
        db, conversation_id, "assistant", llm_response, sources=sources
    )
    
    return ChatResponse(
        message=assistant_message,
        sources=sources,
        conversation_id=conversation_id
    )
```

---

### 4. Dynamic @Mention Sources
**Goal**: Query Qdrant for available sources to show in @mention dropdown

#### Sources Endpoint
```python
# apps/api/app/api/v1/endpoints/sources.py
from fastapi import APIRouter
from typing import List, Optional
from app.services.vector_db import VectorDBService

router = APIRouter()

class Source(BaseModel):
    id: str
    url: str
    title: str
    type: str  # "document", "webpage", "api"
    last_updated: datetime

@router.get("/", response_model=List[Source])
async def list_sources(
    search: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50
):
    """
    Get available sources for @mentions.
    
    Queries Qdrant for unique sources (by URL) and returns
    metadata for each source document.
    """
    vector_db_service = VectorDBService()
    
    # Scroll through collection to get unique sources
    sources = await vector_db_service.get_unique_sources(
        search_query=search,
        doc_type=type,
        limit=limit
    )
    
    return sources
```

---

### 5. Frontend Integration (Zustand)
**Goal**: Global state management for conversations

#### Store Setup
```typescript
// apps/web/stores/chatStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  sources?: any[];
}

interface Conversation {
  id: string;
  title: string;
  space: string;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  messageCount: number;
}

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  loadConversations: () => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  sendMessage: (content: string, useRag: boolean) => Promise<void>;
  createConversation: (title: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  updateConversation: (id: string, data: Partial<Conversation>) => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversation: null,
      messages: [],
      isLoading: false,
      error: null,
      
      loadConversations: async () => {
        set({ isLoading: true });
        try {
          const response = await fetch('/api/conversations');
          const conversations = await response.json();
          set({ conversations, isLoading: false });
        } catch (error) {
          set({ error: error.message, isLoading: false });
        }
      },
      
      loadConversation: async (id: string) => {
        set({ isLoading: true });
        try {
          const response = await fetch(`/api/conversations/${id}`);
          const data = await response.json();
          set({ 
            currentConversation: data,
            messages: data.messages,
            isLoading: false 
          });
        } catch (error) {
          set({ error: error.message, isLoading: false });
        }
      },
      
      sendMessage: async (content: string, useRag: boolean = true) => {
        const { currentConversation } = get();
        set({ isLoading: true });
        
        try {
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              conversation_id: currentConversation?.id,
              message: content,
              use_rag: useRag
            })
          });
          
          const data = await response.json();
          
          // Update messages and conversation
          set(state => ({
            messages: [...state.messages, data.message],
            currentConversation: data.conversation_id 
              ? { ...state.currentConversation, id: data.conversation_id }
              : state.currentConversation,
            isLoading: false
          }));
        } catch (error) {
          set({ error: error.message, isLoading: false });
        }
      },
      
      // ... other actions
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({ currentConversation: state.currentConversation })
    }
  )
);
```

#### Component Integration
```typescript
// apps/web/app/page.tsx
'use client';

import { useEffect } from 'react';
import { useChatStore } from '@/stores/chatStore';
import ChatInterface from '@/components/chat/ChatInterface';

export default function Home() {
  const { 
    loadConversations, 
    loadConversation, 
    currentConversation 
  } = useChatStore();
  
  useEffect(() => {
    loadConversations();
    
    // Load last conversation from localStorage
    const lastConversationId = localStorage.getItem('lastConversationId');
    if (lastConversationId) {
      loadConversation(lastConversationId);
    }
  }, []);
  
  return (
    <div className="flex h-screen">
      <ChatInterface />
    </div>
  );
}
```

---

## 🧪 Testing Strategy

### Backend Tests (TDD)
All endpoints and database operations require tests BEFORE implementation.

#### Example: Conversation Creation Test
```python
# tests/api/v1/endpoints/test_conversations.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

class TestConversationCreation:
    async def test_create_conversation_returns_valid_structure(
        self, test_client: AsyncClient
    ):
        """Test creating a new conversation."""
        # Arrange
        payload = {
            "title": "Test Conversation",
            "space": "work"
        }
        
        # Act
        response = await test_client.post("/api/v1/conversations/", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert data["space"] == "work"
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_conversation_with_initial_message(
        self, test_client: AsyncClient
    ):
        """Test creating conversation with first message."""
        # Arrange
        payload = {
            "title": "Test Conversation",
            "initial_message": {
                "role": "user",
                "content": "Hello, world!"
            }
        }
        
        # Act
        response = await test_client.post("/api/v1/conversations/", json=payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message_count"] == 1
```

### Frontend Tests
```typescript
// apps/web/__tests__/stores/chatStore.test.ts
import { renderHook, act } from '@testing-library/react';
import { useChatStore } from '@/stores/chatStore';

describe('ChatStore', () => {
  beforeEach(() => {
    // Reset store
    useChatStore.setState({ 
      conversations: [], 
      currentConversation: null 
    });
  });
  
  it('should load conversations from API', async () => {
    // Mock fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve([
          { id: '1', title: 'Test Conversation' }
        ])
      })
    );
    
    const { result } = renderHook(() => useChatStore());
    
    await act(async () => {
      await result.current.loadConversations();
    });
    
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0].title).toBe('Test Conversation');
  });
});
```

---

## 📦 Dependencies

### Backend
```toml
# apps/api/pyproject.toml
[tool.poetry.dependencies]
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
asyncpg = "^0.29.0"  # For PostgreSQL
aiosqlite = "^0.19.0"  # For SQLite
```

### Frontend
```json
// apps/web/package.json
{
  "dependencies": {
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@testing-library/react-hooks": "^8.0.1"
  }
}
```

---

## 🚀 Migration Path

### Step 1: Database Setup (Day 1)
1. Create SQLAlchemy models
2. Setup Alembic migrations
3. Initialize database
4. Write database service tests

### Step 2: Conversation API (Days 2-3)
1. Write endpoint tests (RED)
2. Implement endpoints (GREEN)
3. Refactor for quality (REFACTOR)
4. Test with Postman/curl

### Step 3: Chat Integration (Days 4-5)
1. Write chat endpoint tests
2. Implement RAG integration
3. Test message flow
4. Verify source attribution

### Step 4: Frontend State (Days 6-7)
1. Setup Zustand store
2. Write store tests
3. Connect components
4. Test user flows

### Step 5: Polish & Integration (Days 8-10)
1. End-to-end testing
2. Error handling
3. Loading states
4. Performance optimization

---

## ✅ Definition of Done

- [ ] All database migrations run successfully
- [ ] Conversation CRUD endpoints work
- [ ] Messages persist correctly
- [ ] Chat uses RAG system (not Claude SDK)
- [ ] @mentions show real sources
- [ ] Zustand store manages state
- [ ] All tests pass (80%+ coverage)
- [ ] Mobile UI still responsive
- [ ] No breaking changes to existing UI
- [ ] Documentation updated

---

**Next Phase**: [PHASE_2_GRAPH.md](PHASE_2_GRAPH.md)
