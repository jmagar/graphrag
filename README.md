# GraphRAG Monorepo

A complete GraphRAG (Retrieval-Augmented Generation) system with knowledge graph-powered retrieval, web crawling, vector search, and LLM-powered responses. Features a modern chat interface with Mandalorian theme.

## 🎨 UI Preview

The project includes a complete chat interface mockup (`notebooklm-final.html`) featuring:
- 🪖 **Mandalorian (Pedro Pascal) AI assistant avatar**
- 🟢 **Baby Yoda (Grogu) user avatar**
- 🌙 **Clean dark mode** with consistent blue color scheme
- 💬 **Floating input** with enhance prompt feature
- 📱 **Three-panel responsive layout**: Spaces/Tags, Chat, Workflows
- ⚡ **Interactive features**: @mentions, /commands, conversation tabs
- ⌨️ **Keyboard shortcuts** for power users

## Architecture

```
graphrag/
├── apps/
│   ├── web/               # Next.js web interface
│   └── api/               # FastAPI REST API
├── packages/
│   ├── shared-types/      # Shared TypeScript/Python types (future)
│   └── config/            # Shared configs (future)
└── notebooklm-final.html  # UI mockup (ready for integration)
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Firecrawl v2** - Web crawling and scraping
- **Qdrant** - Vector database for semantic search
- **TEI** - Text Embeddings Inference (Qwen 0.6B)
- **Ollama** - Local LLM inference (Qwen 4B)

### Frontend
- **Next.js 15** - React framework
- **TailwindCSS** - Styling
- **shadcn/ui** - UI components
- **Axios** - HTTP client

## Features

### Core Features
✅ **Web Crawling**: Crawl entire websites with Firecrawl v2  
✅ **Auto-Embedding**: Crawled pages are automatically embedded  
✅ **Vector Search**: Semantic search with Qdrant  
✅ **RAG Queries**: Ask questions and get contextual answers  
✅ **Real-time Updates**: Webhooks for crawl progress  
✅ **Monorepo Structure**: Clean separation of concerns

### UI Features
✅ **Modern Chat Interface**: NotebookLM-inspired design  
✅ **Custom Avatars**: Mandalorian AI assistant & Baby Yoda user  
✅ **Dark Mode First**: Optimized for comfortable extended use  
✅ **Smart Input**: @mentions for sources, /commands for actions  
✅ **Enhance Prompt**: AI-powered query refinement  
✅ **Organized Workspace**: Spaces (Work, Play, Dev) and tags  
✅ **Workflow Shortcuts**: Quick access to common tasks  
✅ **Conversation Tabs**: Multiple chat threads with dropdown navigation  

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Running services:
  - Firecrawl (port 4200)
  - Qdrant (port 4203)
  - TEI (port 4207)
  - Ollama (port 4214)

### 1. Install Dependencies

```bash
# Install root dependencies
npm install

# Install frontend dependencies
cd apps/frontend
npm install
cd ../..

# Install backend dependencies
cd apps/backend
pip install -r requirements.txt
# OR using poetry: poetry install
cd ../..
```

### 2. Configure Environment

The root `.env` file contains all service URLs. Backend uses this file directly.

```bash
# .env is already configured, but verify your service URLs
cat .env
```

### 3. Start Services

**Option 1: Start Both (Recommended)**
```bash
npm run dev
# Starts both backend (port 8000) and frontend (port 3000) concurrently
```

**Option 2: Start Individually**

*Frontend only:*
```bash
npm run dev:frontend
# OR: cd apps/frontend && npm run dev
```

*Backend only:*
```bash
npm run dev:backend
# OR: cd apps/backend && source venv/bin/activate && python -m app.main
```

### 4. Open the App

Visit http://localhost:3000 and start crawling!

### 5. Preview the UI Mockup

Open `notebooklm-final.html` in your browser to see the complete chat interface design. This is a static HTML mockup ready to be integrated with the Next.js frontend.

```bash
# Open in your default browser
open notebooklm-final.html
# OR
xdg-open notebooklm-final.html
```

## Usage

### 1. Start a Crawl

1. Enter a URL in the frontend
2. (Optional) Configure advanced options:
   - Include/exclude paths
   - Max depth
   - Max pages
   - Crawl entire domain
3. Click "Crawl"

### 2. Track Progress

- Jobs table shows status (pending → scraping → completed)
- Backend receives webhooks and processes pages automatically
- Each page is embedded and stored in Qdrant

### 3. Query Your Data

Use the backend API to query:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this website about?",
    "limit": 5,
    "use_llm": true
  }'
```

## API Documentation

Backend API docs: http://localhost:8000/docs

### Key Endpoints

**Crawl Management**
- `POST /api/v1/crawl` - Start crawl
- `GET /api/v1/crawl/{id}` - Get status
- `DELETE /api/v1/crawl/{id}` - Cancel crawl

**Query**
- `POST /api/v1/query` - RAG query
- `GET /api/v1/query/collection/info` - Vector DB stats

**Webhooks**
- `POST /api/v1/webhooks/firecrawl` - Firecrawl callbacks

## Development

### Frontend

```bash
cd apps/frontend
npm run dev        # Development server
npm run build      # Production build
npm run lint       # Lint code
```

### Backend

```bash
cd apps/backend
python -m app.main          # Run server
black app/                  # Format code
mypy app/                   # Type check
pytest                      # Run tests (when added)
```

## Project Structure

### Backend (`apps/backend/`)

```
app/
├── main.py                 # FastAPI app
├── core/
│   └── config.py          # Settings (reads .env)
├── api/v1/
│   ├── router.py          # API router
│   └── endpoints/
│       ├── crawl.py       # Crawl endpoints
│       ├── query.py       # RAG endpoints
│       └── webhooks.py    # Webhook handlers
└── services/
    ├── firecrawl.py       # Firecrawl v2 client
    ├── embeddings.py      # TEI service
    ├── vector_db.py       # Qdrant service
    └── llm.py             # Ollama service
```

### Frontend (`apps/frontend/`)

```
app/
├── page.tsx               # Main UI
├── layout.tsx             # Root layout
└── api/
    └── crawl/
        ├── route.ts       # Proxy to backend
        └── status/[jobId]/route.ts
```

## Workflow

1. **User submits URL** → Frontend API → Backend `/crawl`
2. **Backend starts crawl** → Firecrawl v2 API
3. **Firecrawl crawls pages** → Sends webhooks to backend
4. **Backend processes webhook** → Generate embeddings → Store in Qdrant
5. **User queries data** → Backend `/query` → Semantic search → LLM response

## Configuration

### Firecrawl v2 Changes

This system uses **Firecrawl v2** API which has breaking changes from v1:

- Endpoint: `/crawl` (not `/v0/crawl` or `/v1/crawl`)
- Status: `GET /crawl/{id}` (not `/v1/crawl/status/{id}`)
- Webhook format: Simple string URL (not object with `{ url: "..." }`)

### Vector Database

Qdrant collection `graphrag` is auto-created with:
- Vector size: 768 (default, adjust for your embedding model)
- Distance metric: Cosine similarity

### Embeddings

TEI service should use a compatible embedding model. Current setup assumes 768-dimensional embeddings.

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.11+)
- Install dependencies: `pip install -r requirements.txt`
- Verify .env file exists in `apps/backend/`

### Frontend can't connect to backend
- Check backend is running on port 8000
- Verify `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/frontend/.env.local`
- Check CORS settings in backend

### Crawl fails
- Verify Firecrawl service is running
- Check `FIRECRAWL_URL` and `FIRECRAWL_API_KEY` in `.env`
- View backend logs for errors

### Webhooks not received
- Check `WEBHOOK_BASE_URL` in backend `.env`
- Ensure backend is accessible from Firecrawl service
- If Firecrawl is on different machine, use public IP/hostname

## Roadmap

- [ ] Integrate `notebooklm-final.html` UI into Next.js app
- [ ] Connect chat interface to backend API
- [ ] Implement real-time RAG queries in UI
- [ ] Add @mention autocomplete for sources
- [ ] Implement /command system
- [ ] Add conversation persistence
- [ ] Build workflow automation system
- [ ] Add knowledge graph visualization
- [ ] Implement multi-user support

## Screenshots

### Chat Interface
![Chat Interface](docs/screenshots/chat-interface.png) _(Coming soon)_

### Dark Mode
![Dark Mode](docs/screenshots/dark-mode.png) _(Coming soon)_

## License

MIT

## Contributing

Contributions welcome! Please read contributing guidelines first.

---

**This is the way.** 🛡️✨
