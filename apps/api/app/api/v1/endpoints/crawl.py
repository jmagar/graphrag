"""
Crawl management endpoints using Firecrawl v2 API.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
from app.services.firecrawl import FirecrawlService
from app.core.config import settings
from app.dependencies import get_firecrawl_service

router = APIRouter()


class CrawlRequest(BaseModel):
    """Request model for starting a crawl."""

    url: HttpUrl
    includePaths: Optional[List[str]] = None
    excludePaths: Optional[List[str]] = None
    maxDiscoveryDepth: Optional[int] = None
    limit: Optional[int] = 10000
    crawlEntireDomain: Optional[bool] = False
    allowSubdomains: Optional[bool] = False
    scrapeOptions: Optional[Dict[str, Any]] = None


class CrawlResponse(BaseModel):
    """Response model for crawl initiation."""

    success: bool
    id: str
    url: str


class CrawlStatusResponse(BaseModel):
    """Response model for crawl status."""

    status: str
    total: int
    completed: int
    creditsUsed: int
    expiresAt: str
    data: Optional[List[Dict[str, Any]]] = None
    next: Optional[str] = None


@router.post("/", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service)
):
    """
    Start a new crawl job using Firecrawl v2 API.

    The crawl will run asynchronously and send webhooks to our backend
    as pages are crawled. Each page will be automatically embedded and
    stored in Qdrant.
    """
    try:
        # Prepare crawl options
        crawl_options: Dict[str, Any] = {
            "url": str(request.url),
            "webhook": f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/firecrawl",
        }

        # Add optional parameters
        if request.includePaths:
            crawl_options["includePaths"] = request.includePaths
        if request.excludePaths:
            crawl_options["excludePaths"] = request.excludePaths
        if request.maxDiscoveryDepth is not None:
            crawl_options["maxDiscoveryDepth"] = request.maxDiscoveryDepth
        if request.limit is not None:
            crawl_options["limit"] = request.limit
        if request.crawlEntireDomain is not None:
            crawl_options["crawlEntireDomain"] = request.crawlEntireDomain
        if request.allowSubdomains is not None:
            crawl_options["allowSubdomains"] = request.allowSubdomains
        if request.scrapeOptions:
            crawl_options["scrapeOptions"] = request.scrapeOptions

        # Start the crawl using singleton service
        result = await firecrawl_service.start_crawl(crawl_options)

        crawl_id = result["id"]
        return {
            "success": result.get("success", True),
            "id": crawl_id,
            "jobId": crawl_id,  # For frontend compatibility
            "url": result["url"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start crawl: {str(e)}")


@router.get("/{crawl_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(
    crawl_id: str,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service)
):
    """
    Get the status of a crawl job.

    Returns the current status, progress, and any crawled data.
    """
    try:
        status = await firecrawl_service.get_crawl_status(crawl_id)
        return CrawlStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get crawl status: {str(e)}")


@router.delete("/{crawl_id}")
async def cancel_crawl(
    crawl_id: str,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service)
):
    """Cancel a running crawl job."""
    try:
        await firecrawl_service.cancel_crawl(crawl_id)
        return {"success": True, "message": "Crawl cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel crawl: {str(e)}")
