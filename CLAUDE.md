# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GraphRAG is a Retrieval-Augmented Generation (RAG) system that combines web crawling (Firecrawl v2), vector search (Qdrant), embeddings (TEI), and LLM responses (Ollama) in a monorepo architecture with separate frontend and backend applications.

## Repository Structure

```
graphrag/
├── apps/
│   ├── api/          # Python FastAPI backend
│   └── web/          # Next.js 15 frontend
└── packages/         # Future: shared types/configs
```

## Build & Development Commands

**Start both services:**
```bash
npm run dev                    # Starts API (port 8000) and web (port 3000)
```

**Individual services:**
```bash
npm run dev:api               # Backend only
npm run dev:web               # Frontend only
```

**Backend (FastAPI):**
```bash
cd apps/api
uv run python -m app.main     # Run server (uvicorn auto-reload enabled)
uv run black app/             # Format code
uv run mypy app/              # Type checking
uv sync                       # Install/update dependencies
uv sync --dev                 # Include dev dependencies
```

**Frontend (Next.js):**
```bash
cd apps/web
npm run dev                   # Development server (port 3000)
npm run build                 # Production build
npm run lint                  # ESLint
```

**Root-level:**
```bash
npm run kill-ports            # Kill processes on ports 3000 and 8000
npm run build                 # Build all workspaces
npm run lint                  # Lint all workspaces
npm run clean                 # Remove all node_modules
```

## Architecture Overview

### Data Flow: Crawl → Embed → Store

1. **Crawl Initiation**: Frontend → Next.js API route → FastAPI `/api/v1/crawl`
2. **Firecrawl Processing**: Backend starts crawl with webhook URL pointing to `/api/v1/webhooks/firecrawl`
3. **Webhook Processing**:
   - Firecrawl sends `crawl.page` events as each page is crawled
   - Backend receives page data in `webhooks.py:process_crawled_page()`
   - Content is extracted from `markdown` field
   - Document ID generated via MD5 hash of URL
4. **Embedding Pipeline**:
   - TEI service generates 768-dimensional embeddings
   - Embeddings stored in Qdrant with content and metadata
5. **Query Flow**: User query → Embed query → Vector search → Optional LLM response

### Backend Service Architecture

The FastAPI backend uses a service-oriented architecture with clear separation of concerns:

**Service Layer** (`app/services/`):
- `firecrawl.py`: Firecrawl v2 API client (POST /v2/crawl, GET /v2/crawl/{id})
- `embeddings.py`: TEI service wrapper for text-to-vector conversion
- `vector_db.py`: Qdrant client managing collection creation, upsert, and search
- `llm.py`: Ollama client for generating contextual responses

**API Layer** (`app/api/v1/endpoints/`):
- `crawl.py`: Crawl management (start, status, cancel)
- `query.py`: RAG queries combining vector search + LLM
- `webhooks.py`: Firecrawl webhook receiver + background page processor

**Configuration** (`app/core/config.py`):
- Uses Pydantic Settings with `.env` file in root directory
- All service URLs configured via environment variables
- CORS origins include localhost and local network (10.1.0.6)

### Frontend Architecture

**Next.js 15 App Router** structure:
- `app/page.tsx`: Main UI (crawl interface + job status table)
- `app/api/crawl/route.ts`: Proxy to backend `/api/v1/crawl`
- `app/api/crawl/status/[jobId]/route.ts`: Proxy to backend status endpoint

**UI Components**:
- Built with shadcn/ui (Radix UI primitives + Tailwind)
- Advanced options popover for crawler configuration (includes/excludes, maxDepth, maxPages)
- Real-time job status polling (5-second interval via `useEffect`)

**Communication Pattern**:
- Frontend calls Next.js API routes (client-side)
- Next.js API routes proxy to FastAPI backend (server-side)
- This prevents CORS issues and keeps backend URL internal

## Critical Implementation Details

### Firecrawl v2 API Specifics

**Important**: This project uses Firecrawl v2 which has breaking changes from v1:
- Endpoints: `/v2/crawl` (NOT `/crawl` or `/v1/crawl`)
- Status endpoint: `GET /v2/crawl/{id}` (NOT `/v1/crawl/status/{id}`)
- Webhook format: Plain string URL, not object `{ url: "..." }`
- Webhook events: `crawl.started`, `crawl.page`, `crawl.completed`, `crawl.failed`
- Page data structure: `data.markdown` for content, `data.metadata.sourceURL` for URL

### Webhook Processing Pattern

The webhook handler in `webhooks.py:52` uses FastAPI `BackgroundTasks` to process pages asynchronously:
- Immediate acknowledgment returned to Firecrawl
- Page processing (embedding + storage) happens in background
- Each page generates embedding → stored as single Qdrant point
- Document ID: MD5 hash of sourceURL ensures idempotency

### Vector Database Configuration

Qdrant collection (`graphrag`) is auto-created with:
- Vector size: 768 (matches TEI model output)
- Distance metric: Cosine similarity
- Auto-initialization in `VectorDBService.__init__()`

**Payload structure**:
```python
{
  "content": str,      # Full markdown content
  "metadata": dict     # Firecrawl metadata (sourceURL, title, etc.)
}
```

### Service Dependencies

External services must be running:
- **Firecrawl**: Port 4200 (API + webhook receiver)
- **Qdrant**: Port 4203 (vector database)
- **TEI**: Port 4207 (embedding generation)
- **Ollama**: Port 4214 (LLM inference, optional)

Backend health check (`/health`) reports all service URLs.

## Type System Conventions

**Backend (Python)**:
- Pydantic models for all API request/response schemas
- Type hints required on all functions
- No `any` types allowed (per user guidelines)

**Frontend (TypeScript)**:
- No `any` types (use proper types or `unknown`)
- Type inference preferred where clear
- Axios response types explicitly handled

## Error Handling Philosophy

Per user guidelines: **Throw errors early, do not use fallbacks.**

- Backend: Raise `HTTPException` with clear status codes and messages
- Frontend: Display error messages to user (no silent failures)
- No defensive fallbacks that mask real issues

## Development Methodology

**MANDATORY: Test-Driven Development (TDD)**

All new features and bug fixes MUST follow the RED-GREEN-REFACTOR cycle:

1. **RED**: Write a failing test first
   - Backend: pytest test that calls the API endpoint or service method
   - Frontend: Jest/RTL test for component behavior
   - Test MUST fail initially to prove it's testing the right thing

2. **GREEN**: Write minimal code to make the test pass
   - Implement only what's needed to pass the test
   - No extra features or "future-proofing"

3. **REFACTOR**: Clean up the code while keeping tests green
   - Improve structure, remove duplication
   - All tests must continue passing

**API + Mobile First Design**

All features must be designed with these priorities:

1. **API First**: Design and implement the REST API endpoint before any UI
   - Define request/response schemas (Pydantic models)
   - Implement endpoint logic and tests
   - Document in OpenAPI/Swagger before building frontend

2. **Mobile First**: UI must work on mobile viewports first, then scale up
   - Start with mobile layout (320px+)
   - Use responsive Tailwind utilities
   - Test all interactions work with touch
   - Desktop enhancements come after mobile works

**Testing Strategy**

Tests not yet implemented. When adding:
- Backend: pytest with httpx async client for API testing
- Frontend: Jest + React Testing Library for components
- Integration: Test webhook flow with mock Firecrawl responses

**TDD Enforcement**: No PR should be merged without tests. Write the test first, watch it fail, then implement.

## Environment Configuration

### Python Dependency Management

This project uses **[uv](https://github.com/astral-sh/uv)** for fast, reliable Python dependency management:

- **No Poetry or pip-tools**: We use modern PEP 621 `pyproject.toml` with uv
- **Virtual environment**: `.venv` directory (auto-created by `uv sync`)
- **Lock file**: `uv.lock` (committed to repo for reproducibility)
- **Setup**: Run `uv sync --dev` in `apps/api/` to install all dependencies

**Key uv commands:**
```bash
uv sync              # Install dependencies from pyproject.toml
uv sync --dev        # Include dev dependencies (pytest, black, ruff, mypy)
uv add <package>     # Add a new dependency
uv run <command>     # Run command in virtual environment
uv pip list          # List installed packages
```

### Service URLs

The `.env` file at repository root contains all service URLs:
```
FIRECRAWL_URL=http://localhost:4200
FIRECRAWL_API_KEY=fc-...
QDRANT_URL=http://localhost:4203
QDRANT_API_KEY=
TEI_URL=http://localhost:4207
OLLAMA_URL=http://localhost:4214
OLLAMA_MODEL=qwen3:4b
WEBHOOK_BASE_URL=http://localhost:8000
```

Backend reads this file via `pydantic_settings.BaseSettings`.

## Common Development Tasks

**Adding a new crawl option:**
1. Add field to `CrawlRequest` model in `crawl.py:14`
2. Add conditional logic in `start_crawl()` to include in `crawl_options`
3. Update frontend form in `app/page.tsx` advanced options

**Changing embedding model:**
1. Update TEI service to use new model
2. Update vector size in `vector_db.py:28` to match new model dimensions
3. Recreate Qdrant collection (or create migration)

**Adding new metadata to vector storage:**
1. Extract additional fields in `webhooks.py:process_crawled_page()`
2. Pass to `vector_db_service.upsert_document()` metadata dict
3. Query using filters in `query.py` via `VectorDBService.search(filters=...)`

## Known Issues & Gotchas

- **307 Redirects**: FastAPI redirects `/api/v1/crawl` to `/api/v1/crawl/` - frontend includes trailing slash to avoid
- **CORS**: Local network IP (10.1.0.6) hardcoded in CORS origins for LAN access
- **Webhook URL**: Must be accessible from Firecrawl service (use `WEBHOOK_BASE_URL` for containerized setups)
- **Job Status Polling**: Frontend polls every 5 seconds - consider WebSocket for production

## Pre-production Mode

Per user guidelines: **It's okay to break code when refactoring.** This is pre-production.
- No backward compatibility required during refactors
- Breaking changes acceptable when improving architecture
- Focus on correctness and type safety over stability
