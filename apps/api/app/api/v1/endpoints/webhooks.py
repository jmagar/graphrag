"""
Webhook endpoints for receiving callbacks from Firecrawl.
"""

import hmac
import hashlib
import logging
import json
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from typing import Dict
from pydantic import ValidationError
from app.services.document_processor import process_and_store_document, process_and_store_documents_batch
from app.services.redis_service import RedisService
from app.services.language_detection import LanguageDetectionService
from app.core.config import settings
from app.models import (
    WebhookCrawlPage,
    WebhookCrawlCompleted,
    FirecrawlPageData,
)
from app.dependencies import get_redis_service, get_language_detection_service
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature from Firecrawl webhook.

    Args:
        payload: Raw request body as bytes
        signature: X-Firecrawl-Signature header value
        secret: Webhook secret from settings

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)

# Services will be injected via Depends()


def _validate_webhook_security() -> None:
    """
    Validate webhook security configuration.
    
    Raises:
        HTTPException: If webhook secret is not configured in production
    """
    if not settings.FIRECRAWL_WEBHOOK_SECRET:
        if settings.is_production:
            logger.critical("❌ SECURITY: Webhook secret not configured in production")
            raise HTTPException(
                status_code=500,
                detail="Webhook security not properly configured"
            )
        else:
            logger.warning("⚠️ INSECURE: Running webhooks without signature verification in DEBUG mode")


async def process_crawled_page(page_data: FirecrawlPageData):
    """
    Process a crawled page: generate embeddings and store in vector DB.

    Args:
        page_data: Validated Firecrawl page data (Pydantic model)
    """
    content = page_data.markdown
    metadata = page_data.metadata.model_dump()
    source_url = page_data.metadata.sourceURL

    await process_and_store_document(
        content=content,
        source_url=source_url,
        metadata=metadata,
        source_type="crawl"
    )


@router.post("/firecrawl")
async def firecrawl_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    redis: RedisService = Depends(get_redis_service),
    lang: LanguageDetectionService = Depends(get_language_detection_service)
):
    """
    Webhook endpoint for Firecrawl callbacks.

    Firecrawl sends webhooks for:
    - crawl.started: When a crawl begins
    - crawl.page: Each page that is crawled
    - crawl.completed: When the crawl finishes
    - crawl.failed: If the crawl fails

    Security: Verifies X-Firecrawl-Signature header using HMAC-SHA256.
    Signature verification is MANDATORY in production mode.
    """
    try:
        # Validate security configuration
        _validate_webhook_security()
        
        # Verify webhook signature if secret is configured
        if settings.FIRECRAWL_WEBHOOK_SECRET:
            body = await request.body()
            signature = request.headers.get("X-Firecrawl-Signature", "")

            if not verify_webhook_signature(body, signature, settings.FIRECRAWL_WEBHOOK_SECRET):
                logger.warning(
                    "🚨 Invalid webhook signature",
                    extra={
                        "ip": request.client.host if request.client else "unknown",
                        "signature": signature[:20] + "..." if len(signature) > 20 else signature,
                    }
                )
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
            logger.debug("✅ Webhook signature verified")
            # Parse and validate JSON from verified body
            try:
                payload_dict = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in webhook payload: {e}")
                return {"status": "error", "error": "Invalid JSON payload"}
        else:
            # No secret configured - parse directly (DEBUG mode only)
            logger.debug("⚠️ Webhook processed without signature verification (DEBUG mode)")
            try:
                payload_dict = await request.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in webhook payload: {e}")
                return {"status": "error", "error": "Invalid JSON payload"}

        # Validate webhook payload with Pydantic (provides type safety)
        try:
            event_type = payload_dict.get("type")
            if event_type == "crawl.page":
                payload = WebhookCrawlPage(**payload_dict)
            elif event_type == "crawl.completed":
                payload = WebhookCrawlCompleted(**payload_dict)
            else:
                # For other events, use raw dict (backwards compatible)
                payload = payload_dict
        except ValidationError as e:
            logger.error(f"Webhook payload validation error: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")

        crawl_id = payload_dict.get("id")  # Extract crawl_id early for all events

        if event_type == "crawl.started":
            logger.info(f"Crawl started: {crawl_id}")
            return {"status": "acknowledged"}

        elif event_type == "crawl.page":
            # Process the crawled page in the background
            # payload is now a validated WebhookCrawlPage Pydantic model
            page_data_model: FirecrawlPageData = payload.data if isinstance(payload, WebhookCrawlPage) else FirecrawlPageData(**payload.get("data", {}))
            source_url = page_data_model.metadata.sourceURL
            content = page_data_model.markdown
            
            logger.debug(f"📄 Received crawl.page: {source_url}")
            
            # Language filtering (if enabled) - BEFORE processing
            if settings.ENABLE_LANGUAGE_FILTERING and content:
                detected_lang = lang.detect_language(content)
                
                # Check if language is allowed
                is_allowed = (
                    detected_lang in settings.allowed_languages_list or
                    (settings.LANGUAGE_FILTER_MODE == "lenient" and detected_lang == "unknown")
                )
                
                if not is_allowed:
                    # Skip non-English page
                    logger.info(f"🚫 FILTERED ({detected_lang}): {source_url}")
                    
                    # Mark as processed so we skip it in crawl.completed too
                    if crawl_id and source_url:
                        await redis.mark_page_processed(crawl_id, source_url)
                    
                    return {"status": "filtered", "language": detected_lang}
                else:
                    logger.info(f"✅ ALLOWED ({detected_lang}): {source_url}")
            
            # Track this page as processed (for deduplication in crawl.completed)
            if crawl_id and source_url:
                await redis.mark_page_processed(crawl_id, source_url)
                logger.debug(f"Marked page as processed: {source_url}")
            
            # Process immediately if streaming is enabled
            if settings.ENABLE_STREAMING_PROCESSING:
                logger.info(f"⚡ PROCESSING (streaming): {source_url}")
                background_tasks.add_task(process_crawled_page, page_data_model)
                return {"status": "processing"}
            else:
                logger.info(f"📋 QUEUED (batch): {source_url}")
                return {"status": "acknowledged"}

        elif event_type == "crawl.completed":
            # payload is now a validated WebhookCrawlCompleted Pydantic model
            data: list[FirecrawlPageData] = payload.data if isinstance(payload, WebhookCrawlCompleted) else []
            total_pages = len(data)
            logger.info(f"✓ Crawl completed: {crawl_id} ({total_pages} pages)")

            # Process all pages in BATCH, skipping those already processed via streaming
            if data:
                documents = []
                skipped_count = 0
                skipped_languages: Dict[str, int] = {}  # Track filtered languages

                for page_data_model in data:
                    content = page_data_model.markdown
                    metadata = page_data_model.metadata.model_dump()
                    source_url = page_data_model.metadata.sourceURL

                    if not content or not source_url:
                        continue

                    # Check if this page was already processed during streaming
                    if await redis.is_page_processed(crawl_id, source_url):
                        skipped_count += 1
                        logger.debug(f"Skipping already-processed page: {source_url}")
                        continue

                    # Language filtering (if enabled)
                    if settings.ENABLE_LANGUAGE_FILTERING:
                        detected_lang = lang.detect_language(content)
                        
                        # Check if language is allowed
                        is_allowed = (
                            detected_lang in settings.allowed_languages_list or
                            (settings.LANGUAGE_FILTER_MODE == "lenient" and detected_lang == "unknown")
                        )
                        
                        if not is_allowed:
                            skipped_count += 1
                            skipped_languages[detected_lang] = skipped_languages.get(detected_lang, 0) + 1
                            logger.info(f"🚫 FILTERED (batch, {detected_lang}): {source_url}")
                            
                            # Mark as processed so we don't check again
                            await redis.mark_page_processed(crawl_id, source_url)
                            continue
                        else:
                            logger.debug(f"✅ ALLOWED (batch, {detected_lang}): {source_url}")

                    # Page passes all filters - add to batch
                    documents.append({
                        "content": content,
                        "source_url": source_url,
                        "metadata": metadata,
                        "source_type": "crawl"
                    })
                
                # Log filtering statistics
                if skipped_count > 0:
                    logger.info(
                        f"📊 Crawl {crawl_id}: {skipped_count}/{total_pages} pages skipped"
                    )
                
                # Log language filtering details
                if skipped_languages:
                    logger.warning(
                        f"🌍 Crawl {crawl_id}: Filtered {sum(skipped_languages.values())} "
                        f"non-English pages: {skipped_languages}"
                    )
                
                # Process new pages in batch mode
                if documents:
                    logger.info(
                        f"✅ Crawl {crawl_id}: Processing {len(documents)} "
                        f"new pages in batch mode"
                    )
                    background_tasks.add_task(process_and_store_documents_batch, documents)
                else:
                    logger.info(
                        f"✓ Crawl {crawl_id}: All {total_pages} pages "
                        f"already processed (via streaming)"
                    )
                
                # Cleanup tracking data
                await redis.cleanup_crawl_tracking(crawl_id)

            return {
                "status": "completed",
                "pages_processed": total_pages,
                "pages_skipped": skipped_count if data else 0,
            }

        elif event_type == "crawl.failed":
            error = payload.get("error", "Unknown error")
            logger.error(f"✗ Crawl failed: {crawl_id} - {error}")
            
            # Cleanup tracking data on failure
            if crawl_id:
                await redis.cleanup_crawl_tracking(crawl_id)
            
            return {"status": "error", "error": error}

        else:
            logger.warning(f"Unknown webhook event: {event_type}")
            return {"status": "unknown_event"}

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes (401, 400, etc.)
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
