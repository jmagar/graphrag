"""
Scrape endpoint for single-page scraping using Firecrawl v2 API.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, Dict, Any, List
from httpx import TimeoutException, HTTPStatusError

from app.services.firecrawl import FirecrawlService

logger = logging.getLogger(__name__)
router = APIRouter()

# Valid Firecrawl formats according to their API
VALID_FORMATS = {"markdown", "html", "rawHtml", "links", "screenshot"}


def get_firecrawl_service() -> FirecrawlService:
    """
    Dependency injection provider for FirecrawlService.

    Returns a new instance of FirecrawlService for each request.
    This enables proper testing via dependency override.
    """
    return FirecrawlService()


class ScrapeRequest(BaseModel):
    """Request model for scraping a single URL."""

    url: HttpUrl
    formats: Optional[List[str]] = ["markdown", "html"]

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that only allowed formats are used."""
        if v is not None:
            invalid = set(v) - VALID_FORMATS
            if invalid:
                raise ValueError(f"Invalid formats: {invalid}. Valid formats are: {VALID_FORMATS}")
        return v


class ScrapeResponse(BaseModel):
    """Response model for scrape."""

    success: bool
    data: Optional[Dict[str, Any]] = None


@router.post("/", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),
):
    """
    Scrape a single URL and return its content.

    This is a synchronous operation that returns immediately with the scraped content.
    Unlike crawl, this does not store content in the database.
    """
    try:
        # Simplified: formats always has a value (either provided or default)
        options = {"formats": request.formats}

        result = await firecrawl_service.scrape_url(str(request.url), options)

        return {"success": result.get("success", True), "data": result.get("data", {})}

    except TimeoutException as e:
        logger.error(f"Timeout scraping URL {request.url}: {e}")
        raise HTTPException(status_code=504, detail="Request timeout while scraping URL")

    except HTTPStatusError as e:
        logger.error(f"HTTP error scraping URL {request.url}: {e}")
        raise HTTPException(status_code=502, detail=f"Firecrawl API error: {str(e)}")

    except Exception:
        logger.exception(f"Unexpected error scraping URL {request.url}")
        raise HTTPException(status_code=500, detail="Internal server error while scraping URL")
