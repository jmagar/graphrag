"""
Crawl management endpoints using Firecrawl v2 API.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel, HttpUrl, Field, ValidationError
from typing import Optional, Dict, Any, List
from httpx import TimeoutException, HTTPStatusError, ConnectError
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.firecrawl import FirecrawlService
from app.core.config import settings
from app.dependencies import get_firecrawl_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


class CrawlRequest(BaseModel):
    """Request model for starting a crawl."""

    url: HttpUrl
    includePaths: Optional[List[str]] = None
    excludePaths: Optional[List[str]] = None
    maxDiscoveryDepth: Optional[int] = Field(None, ge=1, le=10, description="Maximum depth to crawl (1-10)")
    limit: Optional[int] = Field(100, ge=1, le=10000, description="Maximum number of pages to crawl (1-10000)")
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
@limiter.limit("5/minute")
async def start_crawl(
    http_request: Request,
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),
):
    """
    Start a new crawl job using Firecrawl v2 API.

    The crawl will run asynchronously and send webhooks to our backend
    as pages are crawled. Each page will be automatically embedded and
    stored in Qdrant.

    Rate limit: 5 requests per minute per IP address
    """
    try:
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/firecrawl"
        
        # Prepare crawl options
        crawl_options: Dict[str, Any] = {
            "url": str(request.url),
            "webhook": webhook_url,
        }
        
        logger.info(
            f"🚀 Starting crawl: {request.url}",
            extra={
                "crawl_url": str(request.url),
                "webhook_url": webhook_url,
                "max_depth": request.maxDiscoveryDepth,
                "limit": request.limit,
            }
        )

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

    except ValidationError as e:
        logger.exception("Validation error during crawl initiation")
        raise HTTPException(status_code=422, detail=f"Invalid crawl request: {str(e)}")

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error during crawl initiation")
        raise HTTPException(
            status_code=504, detail="Crawl initiation timed out. Please try again."
        )

    except (ConnectError, HTTPStatusError) as e:
        logger.exception("Network error during crawl initiation")
        status_code = 502 if isinstance(e, ConnectError) else getattr(e.response, 'status_code', 502)
        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to connect to Firecrawl service: {str(e)}"
        )

    except KeyError as e:
        logger.exception("Response parsing error during crawl initiation")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid response from Firecrawl service: missing field {str(e)}",
        )

    except Exception as e:
        logger.exception("Unexpected error during crawl initiation")
        raise HTTPException(status_code=500, detail=f"Failed to start crawl: {str(e)}")


@router.get("/{crawl_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(
    crawl_id: str, firecrawl_service: FirecrawlService = Depends(get_firecrawl_service)
):
    """
    Get the status of a crawl job.

    Returns the current status, progress, and any crawled data.
    """
    try:
        status = await firecrawl_service.get_crawl_status(crawl_id)
        return CrawlStatusResponse(**status)

    except ValidationError as e:
        logger.exception("Validation error parsing crawl status")
        raise HTTPException(status_code=422, detail=f"Invalid status response: {str(e)}")

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error fetching crawl status")
        raise HTTPException(
            status_code=504, detail="Request timed out. Please try again."
        )

    except HTTPStatusError as e:
        logger.exception("HTTP error fetching crawl status")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Crawl job '{crawl_id}' not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Firecrawl service error: {str(e)}"
        )

    except ConnectError:
        logger.exception("Connection error fetching crawl status")
        raise HTTPException(status_code=503, detail="Firecrawl service unavailable")

    except KeyError as e:
        logger.exception("Response parsing error for crawl status")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid response structure: missing field {str(e)}",
        )

    except Exception as e:
        logger.exception("Unexpected error fetching crawl status")
        raise HTTPException(status_code=500, detail=f"Failed to get crawl status: {str(e)}")


@router.delete("/{crawl_id}")
async def cancel_crawl(
    crawl_id: str, firecrawl_service: FirecrawlService = Depends(get_firecrawl_service)
):
    """Cancel a running crawl job."""
    try:
        await firecrawl_service.cancel_crawl(crawl_id)
        return {"success": True, "message": "Crawl cancelled successfully"}

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error cancelling crawl")
        raise HTTPException(
            status_code=504, detail="Cancel request timed out. Please try again."
        )

    except HTTPStatusError as e:
        logger.exception("HTTP error cancelling crawl")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Crawl job '{crawl_id}' not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Firecrawl service error: {str(e)}"
        )

    except ConnectError:
        logger.exception("Connection error cancelling crawl")
        raise HTTPException(status_code=503, detail="Firecrawl service unavailable")

    except Exception as e:
        logger.exception("Unexpected error cancelling crawl")
        raise HTTPException(status_code=500, detail=f"Failed to cancel crawl: {str(e)}")
