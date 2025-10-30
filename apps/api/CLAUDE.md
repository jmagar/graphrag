# GraphRAG API - Backend Guidelines

This file provides guidance to Claude Code when working with the FastAPI backend.

## Application Overview

The GraphRAG API is a FastAPI-based backend that orchestrates:
- **Web crawling** via Firecrawl v2
- **Vector embeddings** via TEI (Text Embeddings Inference)
- **Vector storage** via Qdrant
- **LLM responses** via Ollama (optional)

## Architecture

### Service-Oriented Design

The backend follows a clean service-oriented architecture:

```
app/
├── main.py                    # FastAPI app + CORS + health check
├── core/
│   └── config.py             # Pydantic Settings (env vars)
├── api/
│   └── v1/
│       ├── router.py         # Main API router
│       └── endpoints/        # Route handlers
│           ├── crawl.py      # POST/GET/DELETE crawls
│           ├── query.py      # RAG queries + collection info
│           └── webhooks.py   # Firecrawl webhook receiver
└── services/                 # Business logic layer
    ├── firecrawl.py         # Firecrawl v2 client
    ├── embeddings.py        # TEI embeddings client
    ├── vector_db.py         # Qdrant operations
    └── llm.py               # Ollama LLM client
```

### Service Layer Pattern

Each service is a **singleton class** that encapsulates external API interactions:

- `FirecrawlService`: All Firecrawl v2 API calls
- `EmbeddingsService`: TEI embedding generation
- `VectorDBService`: Qdrant collection management, upsert, search
- `LLMService`: Ollama text generation

**Design Principles**:
- Services are instantiated once per endpoint handler
- Each service method is async (uses `httpx.AsyncClient`)
- No service state except configuration from `settings`
- All methods raise exceptions on errors (no silent failures)

## Critical Implementation Details

### Firecrawl v2 API

**BREAKING CHANGES FROM V1**:
- Endpoints: `/v2/crawl` (not `/v1/crawl`)
- Status: `GET /v2/crawl/{id}` (not `/v1/crawl/status/{id}`)
- Webhook format: Plain string `"http://..."` (not object `{url: "..."}`)
- Events: `crawl.started`, `crawl.page`, `crawl.completed`, `crawl.failed`

**Webhook Data Structure**:
```python
{
  "type": "crawl.page",
  "data": {
    "markdown": str,           # Page content
    "metadata": {
      "sourceURL": str,        # Original URL
      "title": str,
      # ... other metadata
    }
  }
}
```

**Document ID Strategy**: MD5 hash of `sourceURL` ensures idempotency when re-crawling.

### Vector Database (Qdrant)

**Collection Configuration**:
- Name: `graphrag` (from `settings.QDRANT_COLLECTION`)
- Vector size: `768` (matches TEI model output)
- Distance: Cosine similarity
- Auto-initialized in `VectorDBService.__init__()`

**Payload Structure**:
```python
{
  "content": str,      # Full markdown content from Firecrawl
  "metadata": dict     # All Firecrawl metadata (sourceURL, title, etc.)
}
```

**Point ID**: MD5 hash of sourceURL as UUID (ensures uniqueness)

### Webhook Processing Flow

1. **Firecrawl** sends POST to `/api/v1/webhooks/firecrawl`
2. **Endpoint** validates event type (`crawl.page` only)
3. **BackgroundTasks** processes page asynchronously:
   - Extract content from `data.markdown`
   - Generate embedding via TEI
   - Upsert to Qdrant with metadata
4. **200 OK** returned immediately (Firecrawl doesn't wait)

**Why BackgroundTasks**: Firecrawl has timeout; processing may take 1-5s per page.

### Configuration Management

All external service URLs configured via `.env` at **repository root**:

```env
FIRECRAWL_URL=http://localhost:4200
FIRECRAWL_API_KEY=fc-...
QDRANT_URL=http://localhost:4203
QDRANT_API_KEY=
TEI_URL=http://localhost:4207
OLLAMA_URL=http://localhost:4214
OLLAMA_MODEL=qwen3:4b
WEBHOOK_BASE_URL=http://localhost:8000
```

**Pydantic Settings** (`app/core/config.py`):
- Reads `.env` automatically
- Type-safe with validation
- No `any` types allowed
- Fails fast on missing required vars

## API Endpoints

### Crawl Management

**Start Crawl**:
```
POST /api/v1/crawl
Body: {
  "url": "https://example.com",
  "includePaths": ["docs/*"],    # Optional
  "excludePaths": ["blog/*"],    # Optional
  "maxDepth": 3,                 # Optional
  "limit": 100                   # Optional (maxPages)
}
Response: {
  "id": "crawl-uuid",
  "url": "https://example.com"
}
```

**Get Status**:
```
GET /api/v1/crawl/{id}
Response: {
  "status": "scraping" | "completed" | "failed",
  "total": 42,
  "completed": 42,
  "creditsUsed": 42,
  "data": [...]  # Array of crawled pages
}
```

**Cancel Crawl**:
```
DELETE /api/v1/crawl/{id}
Response: {
  "status": "cancelled"
}
```

### RAG Query

**Query Knowledge Base**:
```
POST /api/v1/query
Body: {
  "query": "How do I configure embeddings?",
  "limit": 5,              # Optional: top-k results
  "use_llm": true          # Optional: generate LLM response
}
Response: {
  "query": "...",
  "results": [
    {
      "content": "...",
      "score": 0.85,
      "metadata": {...}
    }
  ],
  "llm_response": "..."    # If use_llm=true
}
```

**Collection Info**:
```
GET /api/v1/query/collection/info
Response: {
  "points_count": 142,
  "vectors_count": 142,
  "indexed_vectors_count": 142
}
```

### Health Check

```
GET /health
Response: {
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "firecrawl": "http://localhost:4200",
    "qdrant": "http://localhost:4203",
    "tei": "http://localhost:4207"
  }
}
```

## Development Workflow

### Running the Server

```bash
# From apps/api:
python -m app.main

# Or with venv:
venv/bin/python -m app.main

# Or from repo root:
npm run dev:api
```

Server runs on `http://0.0.0.0:8000` with auto-reload enabled.

### Testing Philosophy (TDD Required)

**RED-GREEN-REFACTOR**:

1. **RED**: Write failing test first
   ```python
   # tests/test_crawl.py
   async def test_start_crawl_success():
       response = await client.post("/api/v1/crawl", json={"url": "https://example.com"})
       assert response.status_code == 200
       assert "id" in response.json()
   ```

2. **GREEN**: Implement minimal code to pass
   ```python
   # app/api/v1/endpoints/crawl.py
   @router.post("/crawl")
   async def start_crawl(request: CrawlRequest):
       firecrawl = FirecrawlService()
       result = await firecrawl.start_crawl({...})
       return {"id": result["id"], "url": request.url}
   ```

3. **REFACTOR**: Clean up while tests pass

**Test Structure** (not yet implemented):
```
tests/
├── conftest.py              # Fixtures (test client, mock services)
├── test_crawl.py            # Crawl endpoint tests
├── test_query.py            # Query endpoint tests
├── test_webhooks.py         # Webhook handler tests
└── services/
    ├── test_firecrawl.py    # Firecrawl service tests
    ├── test_embeddings.py   # TEI service tests
    └── test_vector_db.py    # Qdrant service tests
```

### Code Quality Tools

```bash
# Format (Black)
black app/

# Type checking (mypy)
mypy app/

# Tests (pytest) - when implemented
pytest
pytest --cov=app tests/
```

## Type System

### Pydantic Models

All request/response schemas are Pydantic models:

```python
from pydantic import BaseModel, Field

class CrawlRequest(BaseModel):
    url: str = Field(..., description="URL to crawl")
    includePaths: list[str] | None = Field(None, description="Paths to include")
    excludePaths: list[str] | None = Field(None, description="Paths to exclude")
    maxDepth: int | None = Field(None, ge=1, le=10)
    limit: int | None = Field(None, ge=1, le=1000, alias="maxPages")
```

**Rules**:
- Use `Field()` for validation and documentation
- Use `|` for unions (Python 3.10+), not `Union`
- Never use `Any` - use `dict[str, Any]` with proper structure
- All async functions must be typed: `async def foo() -> Dict[str, Any]:`

### httpx Response Handling

```python
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=payload, timeout=30.0)
    response.raise_for_status()  # Raises HTTPStatusError on 4xx/5xx
    data: Dict[str, Any] = response.json()
    return data
```

**Never catch and ignore errors** - let them bubble up to FastAPI's exception handler.

## Error Handling

### FastAPI Exceptions

```python
from fastapi import HTTPException

# Bad request
raise HTTPException(status_code=400, detail="Invalid URL format")

# Not found
raise HTTPException(status_code=404, detail=f"Crawl {id} not found")

# Service unavailable
raise HTTPException(status_code=503, detail="Firecrawl service unavailable")
```

### Service Errors

Services raise `httpx.HTTPStatusError` or `httpx.RequestError`:
- Let these propagate to endpoint handlers
- Endpoint wraps in `HTTPException` with appropriate status code
- Never return error as successful response

## Common Development Tasks

### Adding a New Endpoint

1. **Write test** in `tests/test_<module>.py`
2. **Define schema** in endpoint file (Pydantic models)
3. **Implement handler** in `app/api/v1/endpoints/<module>.py`
4. **Register route** (if new module) in `app/api/v1/router.py`

### Adding a New Service

1. **Create service file** in `app/services/<name>.py`
2. **Define service class**:
   ```python
   class MyService:
       def __init__(self):
           self.base_url = settings.MY_SERVICE_URL
       
       async def do_something(self, param: str) -> Dict[str, Any]:
           async with httpx.AsyncClient() as client:
               response = await client.get(f"{self.base_url}/endpoint")
               response.raise_for_status()
               return response.json()
   ```
3. **Add config** to `app/core/config.py`
4. **Write tests** in `tests/services/test_<name>.py`

### Modifying Vector Schema

1. **Update payload** in `webhooks.py:process_crawled_page()`
2. **Update search filters** in `query.py` if needed
3. **Recreate collection** (or write migration):
   ```python
   # In VectorDBService.__init__()
   self.client.recreate_collection(
       collection_name=self.collection_name,
       vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
   )
   ```

## Dependencies

```
fastapi==0.115.0           # Web framework
uvicorn[standard]==0.32.0  # ASGI server
pydantic==2.9.2            # Data validation
pydantic-settings==2.6.0   # Environment config
httpx==0.27.2              # Async HTTP client
qdrant-client==1.12.0      # Vector database
python-dotenv==1.0.1       # .env file loading
python-multipart==0.0.12   # File uploads (future)
```

## Known Issues

### CORS Configuration

CORS origins include local network IP for LAN access:
```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://10.1.0.6:3000",  # Local network
]
```

Update `app/core/config.py` if frontend IP changes.

### Webhook URL in Containers

If running in Docker, `WEBHOOK_BASE_URL` must be accessible from Firecrawl container:
- Use Docker network name (e.g., `http://api:8000`)
- Or use host IP (e.g., `http://10.1.0.6:8000`)

### Trailing Slashes

FastAPI redirects `/api/v1/crawl` → `/api/v1/crawl/` (307).  
Frontend includes trailing slashes to avoid redirect overhead.

## Pre-Production Notes

Per root CLAUDE.md: **Breaking changes are acceptable.**

- Refactor fearlessly - this is pre-production
- No backward compatibility required
- Prioritize correctness over stability
- Focus on type safety and testability

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Pydantic Docs**: https://docs.pydantic.dev
- **Qdrant Docs**: https://qdrant.tech/documentation
- **Firecrawl v2 API**: https://docs.firecrawl.dev/api-reference/v2
