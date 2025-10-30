# GraphRAG Backend

FastAPI backend for GraphRAG system with Firecrawl v2, Qdrant vector database, and TEI embeddings.

## Features

- **Firecrawl v2 Integration**: Start crawls, track status, receive webhooks
- **Automatic Embeddings**: Pages are automatically embedded using TEI
- **Vector Search**: Qdrant for semantic search
- **RAG Queries**: Retrieve relevant documents and generate LLM responses
- **Webhooks**: Real-time processing of crawled pages

## Setup

### 1. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using poetry
poetry install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure your services:

```bash
cp .env.example .env
```

### 3. Run the Server

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Crawl Management

- `POST /api/v1/crawl` - Start a new crawl
- `GET /api/v1/crawl/{id}` - Get crawl status
- `DELETE /api/v1/crawl/{id}` - Cancel a crawl

### Query

- `POST /api/v1/query` - Query the knowledge base with RAG
- `GET /api/v1/query/collection/info` - Get vector DB stats

### Webhooks

- `POST /api/v1/webhooks/firecrawl` - Firecrawl webhook endpoint

### Health

- `GET /health` - Health check

## Architecture

```
app/
├── main.py                 # FastAPI app entry point
├── core/
│   └── config.py          # Settings and configuration
├── api/
│   └── v1/
│       ├── router.py      # Main API router
│       └── endpoints/     # Endpoint modules
│           ├── crawl.py   # Crawl management
│           ├── query.py   # RAG queries
│           └── webhooks.py # Webhook handlers
└── services/
    ├── firecrawl.py       # Firecrawl v2 API client
    ├── embeddings.py      # TEI embeddings
    ├── vector_db.py       # Qdrant operations
    └── llm.py             # Ollama LLM integration
```

## Development

```bash
# Run with auto-reload
venv/bin/python -m app.main

# Or from root:
npm run dev:api

# Format code
black app/

# Type checking
mypy app/

# Tests
pytest
```
