# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GraphRAG is a Retrieval-Augmented Generation (RAG) system that combines web crawling (Firecrawl v2), vector search (Qdrant), embeddings (TEI), and LLM responses (Ollama) in a monorepo architecture with separate frontend and backend applications.

## Repository Structure

```text
graphrag/
├── apps/
│   ├── api/          # Python FastAPI backend
│   └── web/          # Next.js 15 frontend
└── packages/         # Future: shared types/configs
```

## Build & Development Commands

**Start both services:**

```bash
npm run dev                    # Starts API (port 4400) and web (port 4300)
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
npm run dev                   # Development server (port 4300)
npm run build                 # Production build
npm run lint                  # ESLint
```

**Root-level:**

```bash
npm run kill-ports            # Kill processes on ports 4300 and 4400
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
5. **Query Flow**:
   - User query → Check Redis cache for query results
   - If cache miss:
     - Generate embedding via TEI
     - Vector search in Qdrant
     - Cache complete query results in Redis (TTL: QUERY_CACHE_TTL, default 5 minutes)
   - Optional LLM response generation
   - Query result caching provides 10-100x performance improvement on cache hits

### Backend Service Architecture

The FastAPI backend uses a service-oriented architecture with clear separation of concerns:

**Service Layer** (`app/services/`):
- `firecrawl.py`: Firecrawl v2 API client (POST /v2/crawl, GET /v2/crawl/{id})
- `embeddings.py`: TEI service wrapper for text-to-vector conversion
- `vector_db.py`: Qdrant client managing collection creation, upsert, and search
- `llm.py`: Ollama client for generating contextual responses
- `redis_service.py`: Redis client for caching and webhook deduplication
- `language_detection.py`: Language detection with LRU caching

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
- **Redis**: Port 4202 (caching and deduplication) - **Optional, graceful degradation**
- **Qdrant**: Port 4203 (vector database)
- **TEI**: Port 4207 (embedding generation)
- **Ollama**: Port 4214 (LLM inference, optional)

**Redis Usage**:
- Query embedding caching (1 hour TTL)
- Webhook deduplication tracking
- Crawl page processing tracking
- Gracefully degrades if unavailable (logs warning, continues operation)

Backend health check (`/health`) reports all service URLs.

### Query Caching Strategy

**Cache Implementation**: Redis-backed query embedding cache

**How It Works**:
1. **Cache Key Generation**: MD5 hash of query text
2. **Cache Storage**: JSON-serialized embedding vector
3. **TTL**: 3600 seconds (1 hour)
4. **Graceful Degradation**: If Redis unavailable, embedding is generated without caching

**Performance Impact**:
- Cache hit: ~5-10ms (Redis lookup)
- Cache miss: ~100-500ms (TEI embedding generation)
- Hit rate improvement: 50-80% for repeated queries

**Cache Invalidation**:

1. **Time-based (TTL)**: Automatic expiration after 1 hour
   - Ensures embeddings stay fresh
   - Prevents stale cache issues
   - Balances cache hit rate vs. accuracy

2. **Manual Invalidation**: Not currently implemented
   - Future: Add `/api/v1/cache/clear` endpoint
   - Future: Clear cache on model changes

3. **No Invalidation Needed For**:
   - New documents added to Qdrant (queries are independent)
   - Vector database updates (embeddings are query-only)

**Cache Statistics**:

Currently tracked internally but not exposed via API. Future implementation:

```python
# GET /api/v1/cache/stats
{
  "query_embeddings": {
    "hits": 1247,
    "misses": 342,
    "hit_rate": 78.5,
    "cache_size_bytes": 2458624
  },
  "language_detection": {
    "hits": 891,
    "misses": 124,
    "hit_rate": 87.8,
    "cache_size": 245
  }
}
```

**Configuration**:

```env
# .env file
REDIS_HOST=localhost
REDIS_PORT=4202
REDIS_DB=0
REDIS_PASSWORD=  # Optional

# Cache sizes
LANGUAGE_DETECTION_CACHE_SIZE=1000  # In-memory LRU cache
```

**Monitoring**:

```bash
# View cached queries in Redis
redis-cli --scan --pattern "embed:query:*"

# Check cache entry
redis-cli GET embed:query:<hash>

# Monitor cache operations
redis-cli MONITOR | grep embed:query
```

## API Endpoints

### Health Check Endpoints

**Backend (FastAPI):**
- `GET /health` - Returns full health status with service URLs and version
- `HEAD /health` - Lightweight connectivity check (200 OK, no body)

**Frontend (Next.js):**
- `GET /api/health` - Proxies to backend `/health`, returns service status
- `HEAD /api/health` - Lightweight check, proxies to backend GET (no body returned)

**Response Schema:**
```typescript
{
  status: "healthy" | "degraded" | "unhealthy",
  version: string,
  services: {
    firecrawl: string,  // URL
    qdrant: string,     // URL  
    tei: string         // URL
  }
}
```

**Usage:**
- Consumed by `useSystemStatus` hook for periodic health polling
- Use HEAD method for cheap connectivity checks (load balancers, monitoring)
- Frontend returns degraded status if backend is unreachable

**Testing:**
```bash
# Test endpoints
curl http://localhost:4300/api/health      # Frontend GET
curl -I http://localhost:4300/api/health   # Frontend HEAD
curl http://localhost:4400/health          # Backend GET
curl -I http://localhost:4400/health       # Backend HEAD
```

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

**Status**: Comprehensive test suite with 987 test functions across 78 test files

**Backend Testing** (596 test functions across 45 files):
- pytest with httpx async client for API testing
- Sophisticated mocking with respx (HTTP), fakeredis (Redis), unittest.mock
- 73 model validation tests with 100% coverage
- 2785 lines of integration tests
- Comprehensive fixtures in conftest.py (461 lines)
- Test coverage: 78/100 (Good)

**Frontend Testing** (391 test functions across 33 files):
- Jest + React Testing Library for components
- Component tests for chat messages, headers, citations
- Hook tests (useSystemStatus, useMediaQuery)
- Security tests (XSS prevention)
- 70% coverage threshold configured
- Test coverage: 60/100 (Fair, needs expansion)

**Test Coverage Gaps**:
- Backend: cache.py, extract.py, map.py, query.py endpoints need tests
- Frontend: ChatInput.tsx, ClientLayout.tsx, main page.tsx need tests

**TDD Enforcement**: No PR should be merged without tests. Write the test first, watch it fail, then implement.

**Running Tests**:
```bash
# Backend
cd apps/api
uv run pytest                  # Run all tests except integration
uv run pytest -m integration  # Run integration tests only
uv run pytest --cov           # Run with coverage report

# Frontend
cd apps/web
npm test                      # Run Jest tests
npm run test:watch           # Run in watch mode
```

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

```env
FIRECRAWL_URL=http://localhost:4200
FIRECRAWL_API_KEY=fc-...
QDRANT_URL=http://localhost:4203
QDRANT_API_KEY=
TEI_URL=http://localhost:4207
OLLAMA_URL=http://localhost:4214
OLLAMA_MODEL=qwen3:4b
WEBHOOK_BASE_URL=http://localhost:4400

# Redis (optional, for caching)
REDIS_HOST=localhost
REDIS_PORT=4202
REDIS_DB=0
REDIS_PASSWORD=

# Cache configuration
LANGUAGE_DETECTION_CACHE_SIZE=1000
LANGUAGE_DETECTION_SAMPLE_SIZE=2000
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
