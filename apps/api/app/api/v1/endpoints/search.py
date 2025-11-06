"""
Search endpoint for web search using Firecrawl v2 API.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from httpx import TimeoutException, HTTPStatusError, ConnectError
from app.services.firecrawl import FirecrawlService
from app.services.document_processor import process_and_store_documents_batch
from app.dependencies import get_firecrawl_service

logger = logging.getLogger(__name__)
router = APIRouter()


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
    background_tasks: BackgroundTasks,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),
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
                documents.append(
                    {
                        "content": content,
                        "source_url": url,
                        "metadata": item.get("metadata", {}),
                        "source_type": "search",
                    }
                )

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

    except ValidationError as e:
        logger.exception("Validation error during search")
        raise HTTPException(status_code=422, detail=f"Invalid search request: {str(e)}")

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error during search")
        raise HTTPException(
            status_code=504, detail="Search request timed out. Please try again."
        )

    except (ConnectError, HTTPStatusError) as e:
        logger.exception("Network error during search")
        status_code = 502 if isinstance(e, ConnectError) else getattr(e.response, 'status_code', 502)
        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to connect to Firecrawl search service: {str(e)}"
        )

    except KeyError as e:
        logger.exception("Response parsing error during search")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid response from search service: missing field {str(e)}",
        )

    except Exception as e:
        logger.exception("Unexpected error during search")
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")
