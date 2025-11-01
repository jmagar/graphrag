# Webhook Processing Modes: Streaming vs Batching Analysis

**Date**: 2025-10-30
**Question**: When do we stream vs batch? Can we get the best of both worlds?

---

## Current Implementation

### Firecrawl Webhook Behavior

When you start a crawl, Firecrawl v2 sends **multiple webhook events**:

```
1. crawl.started      → Acknowledgment only
2. crawl.page         → Per page as it's crawled (STREAMING)
3. crawl.page         → Another page (STREAMING)
4. crawl.page         → Another page (STREAMING)
   ... (continues for each page)
5. crawl.completed    → All pages included in payload (BATCH)
```

**Key Discovery**: Firecrawl sends **BOTH** individual `crawl.page` events **AND** all pages in `crawl.completed`!

---

## Current Processing Logic

### Mode 1: Individual Streaming (`crawl.page` events)

**Code**: `webhooks.py:52`
```python
elif event_type == "crawl.page":
    page_data = payload.get("data", {})
    background_tasks.add_task(process_crawled_page, page_data)
    return {"status": "processing"}
```

**What happens**:
1. Firecrawl scrapes a page
2. Immediately sends `crawl.page` webhook
3. We process it individually: `process_crawled_page(page_data)`
4. This calls `process_and_store_document()` which wraps it in a 1-item list
5. Calls `process_and_store_documents_batch([single_doc])`
6. TEI batch call with 1 item, Qdrant upsert with 1 item

**Performance**: ~100-150ms per page
**User Experience**: ⚡ Pages appear in search results immediately as they're crawled

---

### Mode 2: Batch Processing (`crawl.completed` event)

**Code**: `webhooks.py:67-83`
```python
elif event_type == "crawl.completed":
    data = payload.get("data", [])  # ALL pages
    
    # Build document list
    documents = []
    for page_data in data:
        content = page_data.get("markdown", "")
        # ... extract metadata
        documents.append({...})
    
    # ONE background task for ALL pages
    if documents:
        background_tasks.add_task(process_and_store_documents_batch, documents)
```

**What happens**:
1. Crawl finishes, Firecrawl sends `crawl.completed` with ALL pages
2. We extract all pages into a list
3. Call `process_and_store_documents_batch(all_pages)`
4. Split into batches of 80 documents
5. Process batches in parallel (up to 10 concurrent)
6. Each batch: 1 TEI call (80 embeddings) + 1 Qdrant upsert (80 docs)

**Performance**: 100 pages ≈ <1 second (2 batches: 80 + 20)
**User Experience**: 🔄 Wait until crawl completes, then all pages available at once

---

## The Problem: DUPLICATE PROCESSING

**CRITICAL ISSUE**: We're processing pages **TWICE**!

1. First time: When `crawl.page` event arrives (streaming)
2. Second time: When `crawl.completed` event arrives (batch)

**Result**: 
- ❌ Wasted compute (2x embedding generation)
- ❌ Wasted API calls (2x TEI, 2x Qdrant)
- ⚠️ Qdrant upserts are idempotent (same doc_id = MD5 of URL), so **no duplicates in DB**
- ⚠️ But still wasteful processing

---

## When Does Each Mode Trigger?

### Current Behavior (Unoptimized)

**Every crawl triggers BOTH modes**:
```
User starts crawl
  ↓
Firecrawl sends: crawl.page, crawl.page, crawl.page... (stream mode)
  ↓
We process each page individually (~100ms each)
  ↓
Firecrawl sends: crawl.completed with ALL pages (batch mode)
  ↓
We process ALL pages again in batches (~<1s total)
  ↓
RESULT: 2x processing, but only 1x storage (Qdrant deduplicates)
```

---

## Best of Both Worlds: Optimization Strategy

### Option 1: Track Processed Pages (Recommended)

**Concept**: Track which pages we've already processed in `crawl.page` events, skip them in `crawl.completed`.

```python
# In-memory cache (or Redis for production)
processed_crawl_pages: Dict[str, Set[str]] = {}  # crawl_id → set of URLs

@router.post("/firecrawl")
async def firecrawl_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    event_type = payload.get("type")
    crawl_id = payload.get("id")
    
    if event_type == "crawl.page":
        page_data = payload.get("data", {})
        source_url = page_data.get("metadata", {}).get("sourceURL")
        
        # Track this page
        if crawl_id not in processed_crawl_pages:
            processed_crawl_pages[crawl_id] = set()
        processed_crawl_pages[crawl_id].add(source_url)
        
        # Process immediately (streaming)
        background_tasks.add_task(process_crawled_page, page_data)
        return {"status": "processing"}
    
    elif event_type == "crawl.completed":
        data = payload.get("data", [])
        
        # Filter out already-processed pages
        already_processed = processed_crawl_pages.get(crawl_id, set())
        new_pages = [
            page for page in data
            if page.get("metadata", {}).get("sourceURL") not in already_processed
        ]
        
        if new_pages:
            print(f"Processing {len(new_pages)} pages not yet streamed")
            documents = [build_document(page) for page in new_pages]
            background_tasks.add_task(process_and_store_documents_batch, documents)
        else:
            print(f"All {len(data)} pages already processed via streaming")
        
        # Cleanup
        processed_crawl_pages.pop(crawl_id, None)
        
        return {"status": "completed", "pages_processed": len(data)}
```

**Benefits**:
- ✅ Fast initial results (streaming as pages arrive)
- ✅ No duplicate processing (track + skip)
- ✅ Handles edge cases (if some pages weren't streamed, batch catches them)
- ✅ Memory efficient (cleanup after crawl.completed)

**Production Enhancement**: Use Redis instead of in-memory dict:
```python
# Track in Redis with TTL
await redis.sadd(f"crawl:{crawl_id}:processed", source_url)
await redis.expire(f"crawl:{crawl_id}:processed", 3600)  # 1 hour TTL
```

---

### Option 2: Choose One Mode via Configuration

**Concept**: Add config to enable/disable streaming mode.

```python
# config.py
ENABLE_STREAMING_PROCESSING: bool = True  # or False for batch-only

# webhooks.py
if event_type == "crawl.page":
    if settings.ENABLE_STREAMING_PROCESSING:
        background_tasks.add_task(process_crawled_page, page_data)
    return {"status": "acknowledged"}  # Just acknowledge, don't process

elif event_type == "crawl.completed":
    # Always process in batch mode (whether streaming was enabled or not)
    # If streaming was on, this will duplicate (but Qdrant deduplicates)
    # If streaming was off, this is the only processing
```

**Trade-offs**:

**Streaming Mode Enabled** (current):
- ✅ Fast time-to-first-result (~100ms per page)
- ✅ Real-time search availability
- ❌ 2x processing (wasteful)
- ❌ Slower overall completion (sequential vs batched)

**Batch-Only Mode**:
- ✅ Fastest overall processing (<1s for 100 pages)
- ✅ No duplicate processing
- ❌ Slower time-to-first-result (wait for entire crawl)
- ❌ No real-time updates

---

### Option 3: Hybrid with Micro-Batching (Best Performance)

**Concept**: Don't process `crawl.page` events individually. Instead, accumulate them in a buffer and process in micro-batches every N seconds or M pages.

```python
# In-memory buffer (or Redis queue)
crawl_page_buffer: Dict[str, List[Dict]] = {}  # crawl_id → pages

async def flush_crawl_buffer(crawl_id: str):
    """Process accumulated pages for a crawl ID."""
    pages = crawl_page_buffer.pop(crawl_id, [])
    if pages:
        documents = [build_document(page) for page in pages]
        await process_and_store_documents_batch(documents)

@router.post("/firecrawl")
async def firecrawl_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    crawl_id = payload.get("id")
    
    if event_type == "crawl.page":
        page_data = payload.get("data", {})
        
        # Add to buffer
        if crawl_id not in crawl_page_buffer:
            crawl_page_buffer[crawl_id] = []
        crawl_page_buffer[crawl_id].append(page_data)
        
        # Flush if buffer reaches threshold (e.g., 10 pages)
        if len(crawl_page_buffer[crawl_id]) >= 10:
            background_tasks.add_task(flush_crawl_buffer, crawl_id)
        
        return {"status": "buffered"}
    
    elif event_type == "crawl.completed":
        # Flush any remaining buffered pages first
        if crawl_id in crawl_page_buffer:
            background_tasks.add_task(flush_crawl_buffer, crawl_id)
        
        # Process completed pages (with deduplication logic from Option 1)
        # ...
```

**Benefits**:
- ✅ Fast time-to-first-batch (~1-2 seconds for first 10 pages)
- ✅ Batched processing efficiency (10 pages in ~150ms)
- ✅ Real-time updates (every 10 pages or 2 seconds)
- ✅ No individual page overhead

---

## Recommendation: **Option 1 + Redis**

**Implementation Priority**: HIGH

### Why This Is Best

1. **User Experience**: Pages appear in search results within ~100ms of being crawled
2. **No Waste**: Skip already-processed pages in `crawl.completed` event
3. **Resilient**: If streaming fails, batch mode catches missed pages
4. **Scalable**: Redis-backed tracking works across multiple backend instances

### Implementation Steps

1. **Add Redis client** to `document_processor.py`:
   ```python
   import redis.asyncio as redis
   
   redis_client = redis.Redis(
       host=settings.REDIS_HOST,
       port=settings.REDIS_PORT,
       decode_responses=True
   )
   ```

2. **Track processed pages**:
   ```python
   async def mark_page_processed(crawl_id: str, source_url: str):
       await redis_client.sadd(f"crawl:{crawl_id}:processed", source_url)
       await redis_client.expire(f"crawl:{crawl_id}:processed", 3600)
   
   async def is_page_processed(crawl_id: str, source_url: str) -> bool:
       return await redis_client.sismember(f"crawl:{crawl_id}:processed", source_url)
   ```

3. **Update webhook handler**:
   ```python
   elif event_type == "crawl.page":
       page_data = payload.get("data", {})
       source_url = page_data.get("metadata", {}).get("sourceURL")
       
       # Mark as processed
       await mark_page_processed(crawl_id, source_url)
       
       # Process immediately
       background_tasks.add_task(process_crawled_page, page_data)
   
   elif event_type == "crawl.completed":
       # Filter already-processed pages
       documents = []
       for page_data in payload.get("data", []):
           source_url = page_data.get("metadata", {}).get("sourceURL")
           if not await is_page_processed(crawl_id, source_url):
               documents.append(build_document(page_data))
       
       if documents:
           background_tasks.add_task(process_and_store_documents_batch, documents)
   ```

---

## Performance Impact

### Current (Unoptimized)
- 100 pages crawled
- Streaming: 100 pages × 100ms = **10 seconds**
- Batch: 100 pages ÷ 80 batch × 150ms = **~300ms**
- **Total compute time**: 10.3 seconds
- **Total processing**: 200 pages processed (100 duplicates)

### Optimized (Option 1)
- 100 pages crawled
- Streaming: 100 pages × 100ms = **10 seconds**
- Batch: **0ms** (all pages already processed, skipped)
- **Total compute time**: 10 seconds
- **Total processing**: 100 pages processed (0 duplicates)

**Savings**: 50% compute time, 50% API calls

---

## Alternative: Disable Streaming if You Don't Need Real-Time

If you're okay waiting for the full crawl to complete (e.g., batch indexing jobs):

```python
# .env
ENABLE_STREAMING_PROCESSING=false
```

Then modify webhook handler:
```python
elif event_type == "crawl.page":
    if settings.ENABLE_STREAMING_PROCESSING:
        background_tasks.add_task(process_crawled_page, page_data)
    return {"status": "acknowledged"}  # Just acknowledge
```

**Result**: Only batch mode runs (fastest overall, no real-time updates)

---

## Summary

**Current State**:
- ❌ Duplicate processing (2x embedding generation, 2x API calls)
- ✅ Fast time-to-first-result (streaming)
- ✅ Qdrant deduplicates storage (no duplicate docs)

**Recommended Solution**: **Option 1 (Track + Skip)**
- ✅ Best of both worlds: Real-time streaming + efficient batch processing
- ✅ No duplicate processing
- ✅ Resilient (batch catches any missed pages)
- ✅ Production-ready with Redis

**Quick Win**: If you don't need real-time, just disable streaming mode for 50% faster overall processing.

---

## Next Steps

1. [ ] Add Redis to infrastructure (already running on steamy-wsl)
2. [ ] Implement page tracking in webhook handler
3. [ ] Add metrics to monitor:
   - Pages processed via streaming
   - Pages processed via batch
   - Pages skipped (already processed)
   - Time-to-index per page
4. [ ] Add configuration flag for streaming on/off
5. [ ] Consider micro-batching (Option 3) for ultimate performance
