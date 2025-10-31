"""
Webhook endpoints for receiving callbacks from Firecrawl.
"""

from fastapi import APIRouter, BackgroundTasks, Request
from typing import Dict, Any
from app.services.document_processor import process_and_store_document, process_and_store_documents_batch

router = APIRouter()


async def process_crawled_page(page_data: Dict[str, Any]):
    """
    Process a crawled page: generate embeddings and store in vector DB.

    Args:
        page_data: Page data from Firecrawl webhook
    """
    content = page_data.get("markdown", "")
    metadata = page_data.get("metadata", {})
    source_url = metadata.get("sourceURL", "")
    
    await process_and_store_document(
        content=content,
        source_url=source_url,
        metadata=metadata,
        source_type="crawl"
    )


@router.post("/firecrawl")
async def firecrawl_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Firecrawl callbacks.

    Firecrawl sends webhooks for:
    - crawl.started: When a crawl begins
    - crawl.page: Each page that is crawled
    - crawl.completed: When the crawl finishes
    - crawl.failed: If the crawl fails
    """
    try:
        payload = await request.json()
        event_type = payload.get("type")

        if event_type == "crawl.started":
            print(f"Crawl started: {payload.get('id')}")
            return {"status": "acknowledged"}

        elif event_type == "crawl.page":
            # Process the crawled page in the background
            page_data = payload.get("data", {})
            background_tasks.add_task(process_crawled_page, page_data)
            return {"status": "processing"}

        elif event_type == "crawl.completed":
            crawl_id = payload.get("id")
            data = payload.get("data", [])
            total_pages = len(data)
            print(f"✓ Crawl completed: {crawl_id} ({total_pages} pages)")

            # Process all pages in BATCH if they weren't sent individually
            if data:
                documents = []
                for page_data in data:
                    content = page_data.get("markdown", "")
                    metadata = page_data.get("metadata", {})
                    source_url = metadata.get("sourceURL", "")
                    
                    if content and source_url:
                        documents.append({
                            "content": content,
                            "source_url": source_url,
                            "metadata": metadata,
                            "source_type": "crawl"
                        })
                
                # ONE background task for ALL pages (batch processing)
                if documents:
                    background_tasks.add_task(process_and_store_documents_batch, documents)

            return {"status": "completed", "pages_processed": total_pages}

        elif event_type == "crawl.failed":
            crawl_id = payload.get("id")
            error = payload.get("error", "Unknown error")
            print(f"✗ Crawl failed: {crawl_id} - {error}")
            return {"status": "error", "error": error}

        else:
            print(f"Unknown webhook event: {event_type}")
            return {"status": "unknown_event"}

    except Exception as e:
        print(f"Webhook processing error: {str(e)}")
        return {"status": "error", "message": str(e)}
