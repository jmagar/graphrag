"""
Search endpoint for web search using Firecrawl v2 API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services.firecrawl import FirecrawlService

router = APIRouter()
firecrawl_service = FirecrawlService()


class SearchRequest(BaseModel):
    """Request model for searching the web."""

    query: str
    limit: Optional[int] = 5
    formats: Optional[List[str]] = ["markdown"]


class SearchResult(BaseModel):
    """Individual search result."""

    url: str
    title: str
    content: str


class SearchResponse(BaseModel):
    """Response model for search."""

    success: bool
    results: List[SearchResult]
    total: int


@router.post("/", response_model=SearchResponse)
async def search_web(request: SearchRequest):
    """
    Search the web and get full page content.

    Returns search results with full content for each page.
    """
    try:
        options = {"limit": request.limit, "formats": request.formats}

        result = await firecrawl_service.search_web(request.query, options)

        raw_results = result.get("data", [])
        results = [
            {
                "url": r.get("url", ""),
                "title": r.get("metadata", {}).get("title", "Untitled"),
                "content": r.get("markdown", r.get("html", "")),
            }
            for r in raw_results
        ]

        return {"success": True, "results": results, "total": len(results)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")
