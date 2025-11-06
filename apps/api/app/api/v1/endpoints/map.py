"""
Map endpoint for getting all URLs from a website using Firecrawl v2 API.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, List, Dict, Any
from httpx import TimeoutException, HTTPStatusError, ConnectError
from app.services.firecrawl import FirecrawlService
from app.dependencies import get_firecrawl_service

logger = logging.getLogger(__name__)
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

    except ValidationError as e:
        logger.exception("Validation error during website mapping")
        raise HTTPException(status_code=422, detail=f"Invalid map request: {str(e)}")

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error during website mapping")
        raise HTTPException(
            status_code=504, detail="Mapping request timed out. Please try again."
        )

    except (ConnectError, HTTPStatusError) as e:
        logger.exception("Network error during website mapping")
        status_code = 502 if isinstance(e, ConnectError) else getattr(e.response, 'status_code', 502)
        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to connect to Firecrawl map service: {str(e)}"
        )

    except KeyError as e:
        logger.exception("Response parsing error during website mapping")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid response from map service: missing field {str(e)}",
        )

    except Exception as e:
        logger.exception("Unexpected error during website mapping")
        raise HTTPException(status_code=500, detail=f"Failed to map website: {str(e)}")
