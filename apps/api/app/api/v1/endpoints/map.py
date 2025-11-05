"""
Map endpoint for getting all URLs from a website using Firecrawl v2 API.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from app.services.firecrawl import FirecrawlService
from app.dependencies import get_firecrawl_service

router = APIRouter()


class MapRequest(BaseModel):
    """Request model for mapping a website."""

    url: HttpUrl
    search: Optional[str] = None
    limit: Optional[int] = None


class MapResponse(BaseModel):
    """Response model for map."""

    success: bool
    urls: List[str]
    total: int


@router.post("/", response_model=MapResponse)
async def map_website(
    request: MapRequest,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),
):
    """
    Map a website to get all URLs.

    Returns a list of all URLs found on the website.
    """
    try:
        options: Dict[str, Any] = {}
        if request.search:
            options["search"] = request.search
        if request.limit:
            options["limit"] = request.limit

        result = await firecrawl_service.map_url(str(request.url), options)

        # Extract URL strings from link objects
        links = result.get("links", [])
        urls = [link["url"] if isinstance(link, dict) else link for link in links]

        return {"success": True, "urls": urls, "total": len(urls)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to map website: {str(e)}")
