"""
Webhook endpoints for receiving callbacks from Firecrawl.
"""
from fastapi import APIRouter, BackgroundTasks, Request
from typing import Dict, Any, List
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
import hashlib

router = APIRouter()
embeddings_service = EmbeddingsService()
vector_db_service = VectorDBService()


async def process_crawled_page(page_data: Dict[str, Any]):
    """
    Process a crawled page: generate embeddings and store in vector DB.
    
    Args:
        page_data: Page data from Firecrawl webhook
    """
    try:
        # Extract content and metadata
        content = page_data.get("markdown", "")
        metadata = page_data.get("metadata", {})
        source_url = metadata.get("sourceURL", "")

        if not content or not source_url:
            print(f"Skipping page with no content or URL: {page_data}")
            return

        # Generate a unique ID for this document
        doc_id = hashlib.md5(source_url.encode()).hexdigest()

        # Generate embedding
        embedding = await embeddings_service.generate_embedding(content)

        # Store in vector database
        await vector_db_service.upsert_document(
            doc_id=doc_id,
            embedding=embedding,
            content=content,
            metadata=metadata,
        )

        print(f"✓ Processed and stored: {source_url}")

    except Exception as e:
        print(f"✗ Failed to process page: {str(e)}")


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
            total_pages = len(payload.get("data", []))
            print(f"✓ Crawl completed: {crawl_id} ({total_pages} pages)")
            
            # Process all pages if they weren't sent individually
            data = payload.get("data", [])
            if data:
                for page_data in data:
                    background_tasks.add_task(process_crawled_page, page_data)
            
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
