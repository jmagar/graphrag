# Firecrawl Async Python SDK - Complete Guide

## Table of Contents
1. [AsyncFirecrawl Class Overview](#asyncfirecrawl-class-overview)
2. [Core Async Methods](#core-async-methods)
3. [Async Patterns & Best Practices](#async-patterns--best-practices)
4. [Concurrent Operations](#concurrent-operations)
5. [Error Handling](#error-handling)
6. [FastAPI Integration](#fastapi-integration)
7. [Migration from Sync to Async](#migration-from-sync-to-async)
8. [Performance Considerations](#performance-considerations)

---

## AsyncFirecrawl Class Overview

The `AsyncFirecrawl` class provides non-blocking async methods that mirror the synchronous `Firecrawl` client. It's built on top of the v2 API and supports all major operations.

### Installation

```bash
pip install firecrawl-py
```

### Basic Initialization

```python
from firecrawl import AsyncFirecrawl

# Initialize with API key
firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

# Or use environment variable FIRECRAWL_API_KEY
firecrawl = AsyncFirecrawl()

# Custom API URL (for self-hosted instances)
firecrawl = AsyncFirecrawl(
    api_key="fc-YOUR-API-KEY",
    api_url="http://localhost:4200"
)
```

### API Surface

The `AsyncFirecrawl` class exposes the following async methods:

**Scraping:**
- `scrape()` - Scrape a single URL
- `batch_scrape()` - Scrape multiple URLs (waiter method)
- `start_batch_scrape()` - Start batch scrape job
- `get_batch_scrape_status()` - Check batch scrape status
- `cancel_batch_scrape()` - Cancel batch scrape job
- `get_batch_scrape_errors()` - Get batch scrape errors

**Crawling:**
- `crawl()` - Crawl a website (waiter method)
- `start_crawl()` - Start crawl job
- `get_crawl_status()` - Check crawl status
- `cancel_crawl()` - Cancel crawl job
- `get_crawl_errors()` - Get crawl errors
- `active_crawls()` - List active crawls
- `crawl_params_preview()` - Preview crawl parameters

**Search & Extract:**
- `search()` - Search the web
- `extract()` - Extract structured data (waiter method)
- `start_extract()` - Start extraction job
- `get_extract_status()` - Check extraction status

**Mapping & Utilities:**
- `map()` - Generate URL list from website
- `get_concurrency()` - Get current concurrency limits
- `get_credit_usage()` - Get credit usage stats
- `get_token_usage()` - Get token usage stats
- `get_queue_status()` - Get queue status

**Watchers:**
- `watcher()` - Create async watcher for real-time updates

---

## Core Async Methods

### 1. Scrape (Single URL)

```python
import asyncio
from firecrawl import AsyncFirecrawl

async def scrape_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Basic scrape
    doc = await firecrawl.scrape(
        "https://firecrawl.dev",
        formats=["markdown", "html"]
    )

    print(doc.get("markdown"))
    print(doc.get("html"))
    print(doc.get("metadata"))

asyncio.run(scrape_example())
```

**Parameters:**
- `url` (str): URL to scrape
- `formats` (List[str]): Output formats (markdown, html, screenshot, links)
- Additional options for screenshots, actions, etc.

**Returns:** Document with requested formats and metadata

### 2. Search

```python
async def search_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    results = await firecrawl.search(
        "firecrawl documentation",
        limit=10
    )

    for result in results.get("web", []):
        print(result["url"], result["title"])

asyncio.run(search_example())
```

**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results

**Returns:** Dict with "web" key containing search results

### 3. Crawl (Complete Website)

#### Option A: Waiter Method (Blocks Until Complete)

```python
async def crawl_waiter_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Blocks until crawl completes
    job = await firecrawl.crawl(
        url="https://docs.firecrawl.dev",
        limit=100,
        poll_interval=2,  # Check status every 2 seconds
        timeout=300       # Timeout after 5 minutes
    )

    print(f"Status: {job.status}")
    print(f"Completed: {job.completed}/{job.total}")

    for doc in job.data:
        print(doc.metadata.source_url if doc.metadata else None)

asyncio.run(crawl_waiter_example())
```

#### Option B: Start + Status (Non-Blocking)

```python
async def crawl_async_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Start crawl (returns immediately)
    started = await firecrawl.start_crawl(
        url="https://docs.firecrawl.dev",
        limit=100,
        scrape_options={
            "formats": ["markdown", "html"]
        }
    )

    print(f"Crawl started: {started.id}")

    # Check status later
    status = await firecrawl.get_crawl_status(started.id)
    print(f"Status: {status.status}")
    print(f"Progress: {status.completed}/{status.total}")

asyncio.run(crawl_async_example())
```

### 4. Batch Scrape (Multiple URLs)

#### Option A: Waiter Method

```python
async def batch_scrape_waiter():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    urls = [
        "https://firecrawl.dev",
        "https://docs.firecrawl.dev",
        "https://firecrawl.dev/blog"
    ]

    # Blocks until all URLs are scraped
    job = await firecrawl.batch_scrape(
        urls,
        formats=["markdown"],
        poll_interval=1,
        timeout=60
    )

    print(f"Status: {job.status}")
    print(f"Completed: {job.completed}/{job.total}")

    for doc in job.data:
        print(doc.get("markdown")[:100])

asyncio.run(batch_scrape_waiter())
```

#### Option B: Start + Status

```python
async def batch_scrape_async():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    urls = [
        "https://firecrawl.dev",
        "https://docs.firecrawl.dev"
    ]

    # Start batch (returns immediately)
    started = await firecrawl.start_batch_scrape(urls)
    print(f"Batch job started: {started.id}")

    # Check status later
    status = await firecrawl.get_batch_scrape_status(started.id)
    print(f"Progress: {status.completed}/{status.total}")

asyncio.run(batch_scrape_async())
```

### 5. Watcher (Real-Time Updates)

```python
async def watcher_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Start crawl first
    started = await firecrawl.start_crawl(
        "https://firecrawl.dev",
        limit=5
    )

    # Watch for updates in real-time
    async for snapshot in firecrawl.watcher(
        started.id,
        kind="crawl",
        poll_interval=2,
        timeout=120
    ):
        if snapshot.status == "completed":
            print("DONE", snapshot.status)
            for doc in snapshot.data:
                source = doc.metadata.source_url if doc.metadata else None
                print(f"  - {source}")
        elif snapshot.status == "failed":
            print("ERROR", snapshot.status)
            break
        else:
            print(f"STATUS: {snapshot.status} ({snapshot.completed}/{snapshot.total})")

asyncio.run(watcher_example())
```

### 6. Map (Generate URL List)

```python
async def map_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    result = await firecrawl.map(
        url="https://firecrawl.dev",
        limit=100
    )

    for url in result.get("links", []):
        print(url)

asyncio.run(map_example())
```

### 7. Extract (Structured Data)

```python
async def extract_example():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Extract with JSON schema
    result = await firecrawl.extract(
        urls=["https://firecrawl.dev"],
        schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "features": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        poll_interval=1,
        timeout=60
    )

    print(result.data[0].get("json"))

asyncio.run(extract_example())
```

---

## Async Patterns & Best Practices

### 1. Using asyncio.run()

For standalone scripts, use `asyncio.run()`:

```python
async def main():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    result = await firecrawl.scrape("https://example.com")
    return result

# Run the async function
result = asyncio.run(main())
```

### 2. Context Managers (Resource Management)

**Note:** The current AsyncFirecrawl implementation does NOT support async context managers (`async with`). Initialize normally and let Python's garbage collector handle cleanup.

```python
# Current pattern (correct)
async def scrape_with_client():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    result = await firecrawl.scrape("https://example.com")
    return result

# NOT supported (will fail)
async def scrape_with_context():
    async with AsyncFirecrawl(api_key="fc-YOUR-API-KEY") as firecrawl:
        result = await firecrawl.scrape("https://example.com")
```

### 3. Error Handling

```python
from firecrawl import AsyncFirecrawl
import asyncio

async def safe_scrape(url: str):
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    try:
        result = await firecrawl.scrape(url)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def main():
    results = await asyncio.gather(
        safe_scrape("https://firecrawl.dev"),
        safe_scrape("https://invalid-url-that-will-fail.com"),
        return_exceptions=True
    )

    for result in results:
        if isinstance(result, Exception):
            print(f"Error: {result}")
        else:
            print(result)

asyncio.run(main())
```

### 4. Timeout Handling

```python
import asyncio

async def scrape_with_timeout():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    try:
        result = await asyncio.wait_for(
            firecrawl.scrape("https://slow-website.com"),
            timeout=30.0  # 30 second timeout
        )
        return result
    except asyncio.TimeoutError:
        print("Scrape timed out after 30 seconds")
        return None

asyncio.run(scrape_with_timeout())
```

---

## Concurrent Operations

### 1. Multiple Scrapes in Parallel

```python
import asyncio
from firecrawl import AsyncFirecrawl

async def scrape_url(firecrawl: AsyncFirecrawl, url: str):
    """Scrape a single URL"""
    try:
        doc = await firecrawl.scrape(url, formats=["markdown"])
        return {
            "url": url,
            "success": True,
            "content": doc.get("markdown", "")[:200]
        }
    except Exception as e:
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

async def scrape_multiple_urls():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    urls = [
        "https://firecrawl.dev",
        "https://docs.firecrawl.dev",
        "https://github.com/mendableai/firecrawl"
    ]

    # Create tasks for all URLs
    tasks = [scrape_url(firecrawl, url) for url in urls]

    # Run concurrently
    results = await asyncio.gather(*tasks)

    for result in results:
        print(f"{result['url']}: {'✓' if result['success'] else '✗'}")

asyncio.run(scrape_multiple_urls())
```

### 2. Multiple Crawls in Parallel

```python
async def crawl_site(firecrawl: AsyncFirecrawl, url: str, name: str):
    """Start and monitor a crawl"""
    started = await firecrawl.start_crawl(url, limit=10)

    # Poll for completion
    while True:
        status = await firecrawl.get_crawl_status(started.id)

        if status.status in ["completed", "failed"]:
            return {
                "name": name,
                "status": status.status,
                "pages": status.completed
            }

        await asyncio.sleep(2)

async def crawl_multiple_sites():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    sites = [
        ("https://firecrawl.dev", "Main Site"),
        ("https://docs.firecrawl.dev", "Docs"),
        ("https://firecrawl.dev/blog", "Blog")
    ]

    # Start all crawls concurrently
    tasks = [
        crawl_site(firecrawl, url, name)
        for url, name in sites
    ]

    results = await asyncio.gather(*tasks)

    for result in results:
        print(f"{result['name']}: {result['status']} - {result['pages']} pages")

asyncio.run(crawl_multiple_sites())
```

### 3. Batch Operations with Rate Limiting

```python
import asyncio
from typing import List, TypeVar, Callable

T = TypeVar('T')

async def run_with_concurrency_limit(
    tasks: List[Callable],
    max_concurrent: int = 5
) -> List[T]:
    """Run async tasks with concurrency limit"""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_task(task):
        async with semaphore:
            return await task()

    return await asyncio.gather(*[limited_task(task) for task in tasks])

async def scrape_many_urls_limited():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    urls = [f"https://example.com/page{i}" for i in range(100)]

    # Create task functions
    tasks = [
        lambda url=url: firecrawl.scrape(url, formats=["markdown"])
        for url in urls
    ]

    # Run with max 10 concurrent requests
    results = await run_with_concurrency_limit(tasks, max_concurrent=10)

    print(f"Scraped {len(results)} URLs")

asyncio.run(scrape_many_urls_limited())
```

### 4. Mixed Operations (Scrape + Crawl + Search)

```python
async def comprehensive_research(query: str, target_url: str):
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Run all operations concurrently
    search_task = firecrawl.search(query, limit=5)
    crawl_task = firecrawl.start_crawl(target_url, limit=10)
    scrape_task = firecrawl.scrape(target_url, formats=["markdown"])

    search_results, crawl_job, scrape_result = await asyncio.gather(
        search_task,
        crawl_task,
        scrape_task
    )

    return {
        "search": search_results,
        "crawl_id": crawl_job.id,
        "scrape": scrape_result
    }

asyncio.run(comprehensive_research("web scraping", "https://firecrawl.dev"))
```

---

## Error Handling

### 1. Graceful Degradation

```python
async def scrape_with_fallback(urls: List[str]):
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    async def safe_scrape(url: str):
        try:
            return await firecrawl.scrape(url, formats=["markdown"])
        except Exception as e:
            return {"error": str(e), "url": url}

    results = await asyncio.gather(
        *[safe_scrape(url) for url in urls],
        return_exceptions=False  # Don't propagate exceptions
    )

    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    return {
        "successful": successful,
        "failed": failed
    }
```

### 2. Retry Logic

```python
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_async(
    func: Callable[[], T],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> T:
    """Retry an async function with exponential backoff"""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff ** attempt)
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    raise last_exception

async def reliable_scrape(url: str):
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    result = await retry_async(
        lambda: firecrawl.scrape(url, formats=["markdown"]),
        max_retries=3,
        delay=2.0,
        backoff=2.0
    )

    return result

asyncio.run(reliable_scrape("https://example.com"))
```

### 3. Exception Types

```python
async def handle_specific_errors():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    try:
        result = await firecrawl.scrape("https://example.com")
        return result
    except ValueError as e:
        # Invalid parameters
        print(f"Invalid parameters: {e}")
        raise
    except ConnectionError as e:
        # Network issues
        print(f"Connection error: {e}")
        raise
    except TimeoutError as e:
        # Operation timed out
        print(f"Timeout: {e}")
        raise
    except Exception as e:
        # Other errors
        print(f"Unexpected error: {e}")
        raise
```

---

## FastAPI Integration

### 1. Basic Async Endpoint

```python
from fastapi import FastAPI, HTTPException
from firecrawl import AsyncFirecrawl
from pydantic import BaseModel, HttpUrl
from typing import Optional

app = FastAPI()

# Initialize client at startup
firecrawl: Optional[AsyncFirecrawl] = None

@app.on_event("startup")
async def startup_event():
    global firecrawl
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup if needed (current SDK doesn't require explicit cleanup)
    pass

class ScrapeRequest(BaseModel):
    url: HttpUrl
    formats: list[str] = ["markdown"]

class ScrapeResponse(BaseModel):
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[dict] = None

@app.post("/api/v1/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    """Scrape a single URL"""
    try:
        result = await firecrawl.scrape(
            str(request.url),
            formats=request.formats
        )

        return ScrapeResponse(
            url=str(request.url),
            markdown=result.get("markdown"),
            html=result.get("html"),
            metadata=result.get("metadata")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Dependency Injection Pattern

```python
from fastapi import FastAPI, Depends, HTTPException
from firecrawl import AsyncFirecrawl
from typing import Annotated

app = FastAPI()

async def get_firecrawl_client() -> AsyncFirecrawl:
    """Dependency that provides AsyncFirecrawl instance"""
    return AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

FirecrawlDep = Annotated[AsyncFirecrawl, Depends(get_firecrawl_client)]

@app.post("/api/v1/scrape")
async def scrape_url(
    url: str,
    firecrawl: FirecrawlDep
):
    """Scrape endpoint with dependency injection"""
    result = await firecrawl.scrape(url, formats=["markdown"])
    return result
```

### 3. Background Tasks for Long Operations

```python
from fastapi import FastAPI, BackgroundTasks
from firecrawl import AsyncFirecrawl
from pydantic import BaseModel
import uuid

app = FastAPI()
firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

# In-memory job storage (use Redis/DB in production)
jobs = {}

class CrawlRequest(BaseModel):
    url: str
    limit: int = 100

class CrawlStartResponse(BaseModel):
    job_id: str
    status: str

async def process_crawl(job_id: str, url: str, limit: int):
    """Background task to process crawl"""
    try:
        jobs[job_id] = {"status": "processing", "url": url}

        # Start crawl
        started = await firecrawl.start_crawl(url, limit=limit)

        # Poll for completion
        while True:
            status = await firecrawl.get_crawl_status(started.id)

            jobs[job_id] = {
                "status": status.status,
                "completed": status.completed,
                "total": status.total,
                "url": url
            }

            if status.status in ["completed", "failed"]:
                jobs[job_id]["data"] = status.data
                break

            await asyncio.sleep(5)

    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.post("/api/v1/crawl", response_model=CrawlStartResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
):
    """Start a crawl in the background"""
    job_id = str(uuid.uuid4())

    background_tasks.add_task(
        process_crawl,
        job_id,
        request.url,
        request.limit
    )

    return CrawlStartResponse(
        job_id=job_id,
        status="started"
    )

@app.get("/api/v1/crawl/{job_id}")
async def get_crawl_status(job_id: str):
    """Get crawl job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]
```

### 4. Webhook Processing

```python
from fastapi import FastAPI, BackgroundTasks, Request
from firecrawl import AsyncFirecrawl
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()
firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

class WebhookEvent(BaseModel):
    success: bool
    type: str
    id: str
    data: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

async def process_crawled_page(event_data: dict):
    """Background processing of crawled page"""
    try:
        # Extract page data
        if event_data.get("data"):
            for page in event_data["data"]:
                content = page.get("markdown", "")
                url = page.get("metadata", {}).get("sourceURL", "")

                # Process content (embed, store, etc.)
                print(f"Processing page: {url}")
                # Add your processing logic here

    except Exception as e:
        print(f"Error processing webhook data: {e}")

@app.post("/api/v1/webhooks/firecrawl")
async def firecrawl_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive Firecrawl webhook events

    Event types:
    - crawl.started
    - crawl.page (per page)
    - crawl.completed
    - crawl.failed
    """
    try:
        event_data = await request.json()
        event = WebhookEvent(**event_data)

        # Immediate acknowledgment
        if event.type == "crawl.page":
            # Process page in background
            background_tasks.add_task(process_crawled_page, event_data)

        elif event.type == "crawl.completed":
            print(f"Crawl completed: {event.id}")

        elif event.type == "crawl.failed":
            print(f"Crawl failed: {event.id} - {event.error}")

        return {"status": "received"}

    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 5. Service Layer Pattern

```python
# app/services/firecrawl.py
from firecrawl import AsyncFirecrawl
from typing import Optional, List
import os

class FirecrawlService:
    """Service wrapper for Firecrawl operations"""

    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        api_url = os.getenv("FIRECRAWL_URL", "https://api.firecrawl.dev")
        self.client = AsyncFirecrawl(api_key=api_key, api_url=api_url)

    async def scrape_url(
        self,
        url: str,
        formats: List[str] = ["markdown"]
    ) -> dict:
        """Scrape a single URL"""
        return await self.client.scrape(url, formats=formats)

    async def start_crawl_job(
        self,
        url: str,
        limit: int = 100,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None
    ) -> dict:
        """Start a crawl job"""
        crawl_options = {"limit": limit}

        if includes:
            crawl_options["includes"] = includes
        if excludes:
            crawl_options["excludes"] = excludes

        started = await self.client.start_crawl(url, **crawl_options)

        return {
            "id": started.id,
            "url": started.url if hasattr(started, "url") else url
        }

    async def get_job_status(self, job_id: str) -> dict:
        """Get crawl job status"""
        status = await self.client.get_crawl_status(job_id)

        return {
            "id": job_id,
            "status": status.status,
            "completed": status.completed,
            "total": status.total,
            "data": status.data if status.status == "completed" else None
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a crawl job"""
        return await self.client.cancel_crawl(job_id)

# app/api/v1/endpoints/crawl.py
from fastapi import APIRouter, HTTPException
from app.services.firecrawl import FirecrawlService
from pydantic import BaseModel

router = APIRouter()
firecrawl_service = FirecrawlService()

class CrawlRequest(BaseModel):
    url: str
    limit: int = 100
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None

@router.post("/crawl")
async def start_crawl(request: CrawlRequest):
    """Start a crawl job"""
    try:
        result = await firecrawl_service.start_crawl_job(
            url=request.url,
            limit=request.limit,
            includes=request.includes,
            excludes=request.excludes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/crawl/{job_id}")
async def get_crawl_status(job_id: str):
    """Get crawl job status"""
    try:
        result = await firecrawl_service.get_job_status(job_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/crawl/{job_id}")
async def cancel_crawl(job_id: str):
    """Cancel a crawl job"""
    try:
        success = await firecrawl_service.cancel_job(job_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Migration from Sync to Async

### Before (Sync Code)

```python
from firecrawl import Firecrawl

def scrape_website(url: str):
    firecrawl = Firecrawl(api_key="fc-YOUR-API-KEY")
    result = firecrawl.scrape(url, formats=["markdown"])
    return result

def crawl_website(url: str):
    firecrawl = Firecrawl(api_key="fc-YOUR-API-KEY")
    job = firecrawl.crawl(url, limit=100)
    return job

# Usage
result = scrape_website("https://example.com")
job = crawl_website("https://example.com")
```

### After (Async Code)

```python
from firecrawl import AsyncFirecrawl
import asyncio

async def scrape_website(url: str):
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    result = await firecrawl.scrape(url, formats=["markdown"])
    return result

async def crawl_website(url: str):
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    job = await firecrawl.crawl(url, limit=100)
    return job

# Usage
async def main():
    result = await scrape_website("https://example.com")
    job = await crawl_website("https://example.com")
    return result, job

result, job = asyncio.run(main())
```

### Migration Checklist

1. **Change imports:** `Firecrawl` → `AsyncFirecrawl`
2. **Add async/await keywords:**
   - Add `async` before function definitions
   - Add `await` before all Firecrawl method calls
3. **Update function calls:**
   - Use `asyncio.run()` for top-level execution
   - Use `await` for async function calls
4. **Replace blocking operations:**
   - Use `asyncio.sleep()` instead of `time.sleep()`
   - Use async context managers where available
5. **Update error handling:**
   - Async exceptions work the same way
   - Use `asyncio.gather()` with `return_exceptions=True` for parallel operations

---

## Performance Considerations

### 1. Connection Pooling

The AsyncFirecrawl client reuses HTTP connections automatically via the underlying HTTP client. No manual configuration needed.

### 2. Concurrency Limits

```python
import asyncio

async def controlled_concurrency():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

    async def limited_scrape(url: str):
        async with semaphore:
            return await firecrawl.scrape(url, formats=["markdown"])

    urls = [f"https://example.com/page{i}" for i in range(100)]
    results = await asyncio.gather(*[limited_scrape(url) for url in urls])

    return results
```

### 3. Memory Management

For large crawls, use streaming/pagination:

```python
from firecrawl.v2.types import PaginationConfig

async def memory_efficient_crawl():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Start crawl
    started = await firecrawl.start_crawl("https://example.com", limit=1000)

    # Fetch in pages
    pagination = PaginationConfig(
        auto_paginate=False,  # Fetch one page at a time
        max_results=100       # Process 100 at a time
    )

    while True:
        status = await firecrawl.get_crawl_status(
            started.id,
            pagination_config=pagination
        )

        # Process this batch
        for doc in status.data:
            # Process document
            pass

        if not status.next or status.status == "completed":
            break
```

### 4. Batch Size Optimization

```python
async def optimal_batch_size():
    """
    Recommendations:
    - Scrape: 10-20 concurrent requests
    - Batch scrape: Use native batch_scrape() for up to 1000 URLs
    - Crawl: Start multiple crawls in parallel (5-10 max)
    """
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Good: Use batch_scrape for many URLs
    urls = [f"https://example.com/page{i}" for i in range(500)]
    job = await firecrawl.batch_scrape(
        urls,
        formats=["markdown"],
        poll_interval=2,
        timeout=600
    )

    return job
```

### 5. Monitoring & Metrics

```python
import time
from typing import Dict, Any

class FirecrawlMetrics:
    def __init__(self):
        self.requests = 0
        self.errors = 0
        self.total_time = 0.0

    async def tracked_request(self, coro):
        """Track request metrics"""
        start = time.time()
        self.requests += 1

        try:
            result = await coro
            self.total_time += time.time() - start
            return result
        except Exception as e:
            self.errors += 1
            self.total_time += time.time() - start
            raise

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.requests,
            "errors": self.errors,
            "avg_time": self.total_time / self.requests if self.requests > 0 else 0,
            "error_rate": self.errors / self.requests if self.requests > 0 else 0
        }

async def monitored_scraping():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    metrics = FirecrawlMetrics()

    urls = ["https://example.com/page" + str(i) for i in range(10)]

    tasks = [
        metrics.tracked_request(firecrawl.scrape(url, formats=["markdown"]))
        for url in urls
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    print(metrics.get_stats())
    return results
```

---

## Advanced Patterns

### 1. Producer-Consumer with AsyncFirecrawl

```python
import asyncio
from asyncio import Queue

async def producer(queue: Queue, urls: List[str]):
    """Add URLs to queue"""
    for url in urls:
        await queue.put(url)

    # Signal completion
    await queue.put(None)

async def consumer(
    queue: Queue,
    firecrawl: AsyncFirecrawl,
    worker_id: int
):
    """Consume URLs and scrape them"""
    while True:
        url = await queue.get()

        if url is None:
            queue.task_done()
            break

        try:
            result = await firecrawl.scrape(url, formats=["markdown"])
            print(f"Worker {worker_id}: Scraped {url}")
        except Exception as e:
            print(f"Worker {worker_id}: Error scraping {url} - {e}")
        finally:
            queue.task_done()

async def producer_consumer_pattern():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    queue = Queue(maxsize=100)

    urls = [f"https://example.com/page{i}" for i in range(1000)]

    # Start producer
    producer_task = asyncio.create_task(producer(queue, urls))

    # Start 10 consumer workers
    consumers = [
        asyncio.create_task(consumer(queue, firecrawl, i))
        for i in range(10)
    ]

    # Wait for completion
    await producer_task
    await queue.join()

    # Cancel consumers
    for c in consumers:
        c.cancel()

asyncio.run(producer_consumer_pattern())
```

### 2. Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func):
        """Execute function with circuit breaker"""
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

async def scrape_with_circuit_breaker():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")
    breaker = CircuitBreaker(failure_threshold=3, timeout=30)

    async def scrape():
        return await firecrawl.scrape("https://example.com", formats=["markdown"])

    try:
        result = await breaker.call(scrape)
        return result
    except Exception as e:
        print(f"Circuit breaker prevented call: {e}")
        return None
```

---

## Summary

### Key Takeaways

1. **AsyncFirecrawl mirrors Firecrawl:** Same methods, just add `async`/`await`
2. **No context manager support:** Initialize normally, cleanup is automatic
3. **Use asyncio.gather() for concurrency:** Run multiple operations in parallel
4. **FastAPI integration is seamless:** Use async endpoints with dependency injection
5. **Webhooks for real-time processing:** Use BackgroundTasks for async processing
6. **Service layer pattern recommended:** Wrap AsyncFirecrawl in a service class
7. **Rate limiting is important:** Use semaphores to control concurrency
8. **Error handling is critical:** Always handle exceptions gracefully

### Common Pitfalls

1. **Forgetting `await`:** Always await async calls
2. **Blocking operations:** Don't use `time.sleep()`, use `asyncio.sleep()`
3. **Too much concurrency:** Limit concurrent requests to avoid rate limits
4. **Memory leaks:** For large crawls, use pagination to process in batches
5. **Sync in async context:** Don't call sync Firecrawl methods in async functions

### Best Practices

1. Initialize AsyncFirecrawl at application startup (FastAPI)
2. Use dependency injection for testability
3. Implement retry logic with exponential backoff
4. Use circuit breakers for external API resilience
5. Monitor metrics (requests, errors, latency)
6. Process webhook data in background tasks
7. Use type hints for better IDE support
8. Implement proper logging for debugging

---

## Additional Resources

- [Firecrawl Official Documentation](https://docs.firecrawl.dev/sdks/python)
- [Firecrawl Python SDK on PyPI](https://pypi.org/project/firecrawl-py/)
- [FastAPI Async Documentation](https://fastapi.tiangolo.com/async/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
