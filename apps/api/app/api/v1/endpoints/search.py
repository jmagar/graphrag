"""
Search endpoint for web search using Firecrawl v2 API.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.services.firecrawl import FirecrawlService
from app.services.document_processor import process_and_store_documents_batch

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
async def search_web(
    request: SearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Search the web and get full page content.

    All search results are automatically stored in the knowledge base via background tasks.
    """
    try:
        options = {"limit": request.limit, "formats": request.formats}

        result = await firecrawl_service.search_web(request.query, options)

        raw_results = result.get("data", [])
        
        # Prepare batch of documents to store
        documents = []
        for item in raw_results:
            content = item.get("markdown", item.get("html", ""))
            url = item.get("url", "")
            
            if content and url:
                documents.append({
                    "content": content,
                    "source_url": url,
                    "metadata": item.get("metadata", {}),
                    "source_type": "search"
                })
        
        # Store ALL documents in ONE background task (batch processing)
        if documents:
            background_tasks.add_task(process_and_store_documents_batch, documents)
        
        # Format response
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
