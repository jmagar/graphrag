# GraphRAG Implementation Plan

**Version**: 1.0  
**Date**: 2025-10-30  
**Status**: Ready for Implementation  

---

## 📋 Executive Summary

This implementation plan transforms our current **traditional RAG system** into a **true GraphRAG** with Microsoft Research-inspired knowledge graph integration, while completing chat UI backend integration and establishing robust TDD practices.

### Current State
- ✅ **Frontend**: Production-ready chat UI (25+ components, 100% mobile optimized)
- ✅ **Vector Search**: Functional RAG pipeline (Firecrawl → TEI → Qdrant → Ollama)
- ⚠️ **Testing**: ~5% coverage (CRITICAL - must fix first)
- ❌ **Knowledge Graph**: None (despite "GraphRAG" name)
- ❌ **Persistence**: Conversations lost on refresh

### Transformation Goal
Convert from **vector-only RAG** to **hybrid GraphRAG**:
- Add entity extraction (spaCy/LLM)
- Integrate graph database (Neo4j)
- Implement hybrid retrieval (vector + graph)
- Build knowledge graph visualization
- Create workflow automation system

---

## 🎯 Implementation Phases

### Phase 0: Testing Foundation (Weeks 1-2) ⚠️ CRITICAL FIRST
**Priority**: Must complete before any new features

Establish TDD infrastructure:
- Backend: pytest, fixtures, mocks, coverage tools
- Frontend: Jest, React Testing Library, test utilities
- CI/CD: GitHub Actions, automated testing, coverage reports
- **Target**: 80% backend coverage, 70% frontend coverage

📄 **[Detailed Plan →](docs/implementation/PHASE_0_TESTING.md)**

---

### Phase 1: Backend Integration (Weeks 3-4)
**Goal**: Connect chat UI to real RAG system, add persistence

Deliverables:
- Conversation persistence (PostgreSQL/SQLite)
- Message history API (CRUD operations)
- RAG integration in chat (replace Claude SDK direct calls)
- Dynamic @mention sources (query Qdrant)
- Zustand state management

📄 **[Detailed Plan →](docs/implementation/PHASE_1_BACKEND.md)**

---

### Phase 2: Knowledge Graph Core (Weeks 5-8)
**Goal**: Transform into true GraphRAG with hybrid retrieval

Deliverables:
- Entity extraction pipeline (spaCy NER + LLM validation)
- Neo4j integration (graph database)
- Relationship extraction (subject-predicate-object triplets)
- Hybrid query system (vector + graph)
- Graph query API endpoints

📄 **[Detailed Plan →](docs/implementation/PHASE_2_GRAPH.md)**

---

### Phase 3: Visualization & Commands (Weeks 9-11)
**Goal**: Expose graph in UI, make commands functional

Deliverables:
- Knowledge graph visualization (React Flow)
- Command execution system (7 commands)
- Spaces & tags functionality
- Graph exploration UI
- Citation click-through

📄 **[Detailed Plan →](docs/implementation/PHASE_3_VISUALIZATION.md)**

---

### Phase 4: Workflow Automation (Weeks 12-13)
**Goal**: Turn workflow cards into functional automations

Deliverables:
- Workflow engine (YAML definitions)
- 7 workflow templates (Research, Document, Mind Map, Graph, Plan, PRD, Tasks)
- Workflow execution API
- Progress tracking UI
- Result artifacts

📄 **[Detailed Plan →](docs/implementation/PHASE_4_WORKFLOWS.md)**

---

### Phase 5: Production Readiness (Week 14)
**Goal**: Polish, deploy, document

Deliverables:
- Multi-threading UI (conversation list)
- Export/share functionality
- Docker Compose deployment
- Production documentation
- Performance optimization

---

## 📊 Research Findings

Six specialized agents investigated the codebase in parallel:

### Agent 1: Backend API Status
- **Found**: 7 FastAPI endpoints, 5 services, webhook processing
- **Gap**: Webhook has ZERO tests (high risk), no conversation API
- **Verdict**: Functional but untested, needs persistence layer

### Agent 2: Frontend Web App Status
- **Found**: 25+ React components, excellent mobile optimization
- **Gap**: Disconnected from backend RAG (uses Claude SDK directly)
- **Verdict**: UI ready, needs backend integration

### Agent 3: Chat Interface Integration
- **Found**: Complete UI (@mentions, /commands, artifacts, streaming)
- **Gap**: No dynamic data, hardcoded sources, no real RAG queries
- **Verdict**: Needs API integration and state management

### Agent 4: Testing Infrastructure
- **Found**: 1 test file (test_stats.py), minimal pytest setup
- **Gap**: No conftest.py, no mocks, no frontend tests, no CI/CD
- **Verdict**: CRITICAL BLOCKER - must establish TDD first

### Agent 5: Advanced Features & Roadmap
- **Found**: Vector search works, UI placeholders for workflows/spaces
- **Gap**: No knowledge graph, no entity extraction, no graph DB
- **Verdict**: Traditional RAG, not GraphRAG - needs transformation

### Agent 6: Configuration & DevOps
- **Found**: Complete .env config, all services accessible
- **Gap**: No Docker Compose, no CI/CD, no deployment docs
- **Verdict**: Dev-ready, needs production infrastructure

📄 **[Full Research Reports →](docs/implementation/RESEARCH_FINDINGS.md)**

---

## 🏗️ Architecture Changes

### New Backend Services
```
apps/api/app/
├── db/
│   ├── models.py              # SQLAlchemy models (NEW)
│   ├── connection.py          # Database connection (NEW)
│   └── migrations/            # Alembic migrations (NEW)
├── services/
│   ├── entity_extractor.py    # spaCy NER (NEW)
│   ├── graph_db.py            # Neo4j client (NEW)
│   ├── command_handler.py     # Command execution (NEW)
│   ├── workflow_engine.py     # Workflow automation (NEW)
│   └── (existing services)
├── api/v1/endpoints/
│   ├── conversations.py       # Conversation CRUD (NEW)
│   ├── sources.py             # Source management (NEW)
│   ├── graph.py               # Graph queries (NEW)
│   ├── commands.py            # Command execution (NEW)
│   └── workflows.py           # Workflow API (NEW)
```

### New Frontend Structure
```
apps/web/
├── stores/
│   ├── chatStore.ts           # Zustand global state (NEW)
│   └── workflowStore.ts       # Workflow state (NEW)
├── components/
│   └── graph/
│       └── KnowledgeGraphView.tsx  # React Flow graph (NEW)
├── hooks/
│   ├── useConversations.ts    # Conversation management (NEW)
│   └── useCommands.ts         # Command execution (NEW)
```

### Database Schemas

**PostgreSQL/SQLite**:
```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  title VARCHAR(255),
  space VARCHAR(50),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  role VARCHAR(10),
  content TEXT,
  created_at TIMESTAMP
);

CREATE TABLE conversation_tags (
  conversation_id UUID,
  tag VARCHAR(50),
  PRIMARY KEY (conversation_id, tag)
);
```

**Neo4j Graph**:
```cypher
// Nodes
(:Entity {id, text, type, source_url})
(:Document {id, url, title})

// Relationships
(:Entity)-[:MENTIONED_IN]->(:Document)
(:Entity)-[:RELATED_TO {type}]->(:Entity)
```

---

## 📦 New Dependencies

### Backend (apps/api)
```bash
# Add to pyproject.toml using uv
cd apps/api
uv add spacy neo4j alembic sqlalchemy
uv add --dev pytest-cov pytest-mock respx
```

Resulting `pyproject.toml`:
```toml
[project]
dependencies = [
  "spacy>=3.7.0",
  "neo4j>=5.14.0",
  "alembic>=1.12.0",
  "sqlalchemy>=2.0.0",
  # existing dependencies...
]

[project.optional-dependencies]
dev = [
  "pytest-cov>=4.1.0",
  "pytest-mock>=3.12.0",
  "respx>=0.20.0",
  # existing dev dependencies...
]
```

### Frontend (apps/web)
```json
// Add to package.json
"dependencies": {
  "reactflow": "^11.10.0",
  "zustand": "^4.4.0"
},
"devDependencies": {
  "jest": "^29.7.0",
  "@testing-library/react": "^14.0.0",
  "@testing-library/jest-dom": "^6.1.0",
  "@testing-library/user-event": "^14.5.0"
}
```

---

## 🎯 Success Metrics

### Testing Coverage
- ✅ Backend: 80%+ line coverage
- ✅ Frontend: 70%+ line coverage
- ✅ CI/CD blocks PRs below threshold

### Performance Targets
- ✅ Hybrid query response: <1 second
- ✅ Graph visualization load: <2 seconds
- ✅ Conversation load: <100ms
- ✅ Entity extraction: <500ms per page

### Accuracy Goals
- ✅ Entity extraction precision: 85%+
- ✅ RAG answer quality improvement: 30%+ vs pure vector
- ✅ Workflow success rate: 95%+

---

## ⚠️ Risk Mitigation

### High-Risk Items

1. **Testing Debt (CRITICAL)**
   - Risk: New features built on untested foundation
   - Mitigation: Phase 0 mandatory before any features
   - Enforcement: CI/CD blocks PRs without tests

2. **Knowledge Graph Complexity**
   - Risk: Neo4j adds operational overhead
   - Mitigation: Start with NetworkX (in-memory), migrate to Neo4j later
   - Fallback: Pure vector search if graph fails

3. **Entity Extraction Accuracy**
   - Risk: spaCy may miss domain-specific entities
   - Mitigation: Hybrid approach (spaCy + LLM validation)
   - Monitoring: Track precision/recall metrics

4. **Migration Impact**
   - Risk: Breaking changes during refactor
   - Mitigation: Feature flags, gradual rollout
   - Note: Pre-production mode allows breaking changes

---

## 📅 Timeline Overview

| Phase | Duration | Priority | Status |
|-------|----------|----------|--------|
| Phase 0: Testing | 2 weeks | CRITICAL | 🔴 Not Started |
| Phase 1: Backend | 2 weeks | High | ⚪ Blocked |
| Phase 2: Graph | 4 weeks | High | ⚪ Blocked |
| Phase 3: Visualization | 3 weeks | Medium | ⚪ Blocked |
| Phase 4: Workflows | 2 weeks | Medium | ⚪ Blocked |
| Phase 5: Production | 1 week | Low | ⚪ Blocked |
| **Total** | **14 weeks** | - | - |

---

## 🚀 Getting Started

### Prerequisites
- All current services running (Firecrawl, Qdrant, TEI, Ollama)
- Development environment setup (Node.js 18+, Python 3.11+)
- Git branch: `feat/graphrag-implementation`

### Step 1: Review Phase 0 Plan
Read the detailed testing foundation plan:
```bash
cat docs/implementation/PHASE_0_TESTING.md
```

### Step 2: Setup Testing Infrastructure (Day 1)
```bash
cd apps/api
uv add --dev pytest-cov pytest-mock respx
```

### Step 3: Create Test Fixtures (Day 1-2)
Follow TDD examples in Phase 0 documentation.

### Step 4: Write Tests for Existing Code (Days 3-10)
Priority order:
1. Webhooks (highest risk - no tests)
2. Service layer (enables mocking)
3. API endpoints
4. Frontend routes

---

## 📚 Documentation Structure

This plan is broken into focused documents:

- **IMPLEMENTATION_PLAN.md** (this file) - Overview and navigation
- **docs/implementation/PHASE_0_TESTING.md** - Testing foundation
- **docs/implementation/PHASE_1_BACKEND.md** - Backend integration
- **docs/implementation/PHASE_2_GRAPH.md** - Knowledge graph
- **docs/implementation/PHASE_3_VISUALIZATION.md** - UI features
- **docs/implementation/PHASE_4_WORKFLOWS.md** - Workflow automation
- **docs/implementation/RESEARCH_FINDINGS.md** - Agent reports

---

## ✅ Definition of Done

A feature is complete when:
1. ✅ Tests written first (RED phase)
2. ✅ Implementation passes tests (GREEN phase)
3. ✅ Code refactored for quality (REFACTOR phase)
4. ✅ API documented in OpenAPI/Swagger
5. ✅ Mobile-responsive UI tested (320px+)
6. ✅ Error handling with user-facing messages
7. ✅ PR approved + CI/CD passes

---

## 🤝 Contributing

Follow the TDD workflow:
1. Create feature branch from `feat/graphrag-implementation`
2. Write failing test first (RED)
3. Implement minimal code to pass (GREEN)
4. Refactor while keeping tests green (REFACTOR)
5. Submit PR with tests + implementation
6. Wait for CI/CD approval

---

## 📞 Support

Questions about implementation:
- Review detailed phase documents in `docs/implementation/`
- Check research findings for context
- Consult CLAUDE.md for development guidelines
- Reference README.md for architecture overview

---

**This is the way.** 🛡️✨
