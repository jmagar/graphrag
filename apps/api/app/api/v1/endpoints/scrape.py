"""
Scrape endpoint for single-page scraping using Firecrawl v2 API.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
from app.services.firecrawl import FirecrawlService

router = APIRouter()
firecrawl_service = FirecrawlService()


class ScrapeRequest(BaseModel):
    """Request model for scraping a single URL."""
    url: HttpUrl
    formats: Optional[List[str]] = ["markdown", "html"]


class ScrapeResponse(BaseModel):
    """Response model for scrape."""
    success: bool
    data: Optional[Dict[str, Any]] = None


@router.post("/", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    """
    Scrape a single URL and return its content.
    
    This is a synchronous operation that returns immediately with the scraped content.
    Unlike crawl, this does not store content in the database.
    """
    try:
        options = {}
        if request.formats:
            options["formats"] = request.formats

        result = await firecrawl_service.scrape_url(str(request.url), options)
        
        return {
            "success": result.get("success", True),
            "data": result.get("data", {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape URL: {str(e)}")
