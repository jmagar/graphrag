"""
Extract endpoint for structured data extraction using Firecrawl v2 API.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl

from app.services.firecrawl import FirecrawlService
from app.services.document_processor import process_and_store_document

router = APIRouter()
logger = logging.getLogger(__name__)


def get_firecrawl_service() -> FirecrawlService:
    """Dependency provider for FirecrawlService."""
    return FirecrawlService()


class ExtractRequest(BaseModel):
    """Request model for extracting structured data."""

    url: HttpUrl
    extraction_schema: Dict[str, Any] = Field(..., alias="schema")
    formats: Optional[List[str]] = ["markdown"]


class ExtractResponse(BaseModel):
    """Response model for extract."""

    success: bool
    data: Dict[str, Any]


@router.post("/", response_model=ExtractResponse)
async def extract_data(
    request: ExtractRequest,
    background_tasks: BackgroundTasks,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),
):
    """
    Extract structured data from a webpage.

    Uses natural language or JSON schema to extract specific data.
    Extracted data is automatically stored in the knowledge base via background task.
    """
    try:
        # Build scrapeOptions for Firecrawl v2 API
        scrape_options = {}
        if request.formats:
            scrape_options["formats"] = request.formats

        # Firecrawl v2 API expects urls as array and formats under scrapeOptions
        result = await firecrawl_service.extract_data(
            [str(request.url)],
            request.extraction_schema,
            {"scrapeOptions": scrape_options} if scrape_options else None,
        )

        # Store extracted data in background
        data = result.get("data", {})

        # Convert structured data to JSON string for embedding
        content = json.dumps(data, indent=2)

        background_tasks.add_task(
            process_and_store_document,
            content=content,
            source_url=str(request.url),
            metadata={"extraction_schema": request.extraction_schema, **data.get("metadata", {})},
            source_type="extract",
        )

        return {"success": True, "data": data}

    except (ValueError, TypeError) as e:
        logger.exception("Validation error during extraction")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    except asyncio.TimeoutError:
        logger.exception("Timeout error during extraction")
        raise HTTPException(
            status_code=504, detail="Extraction request timed out. Please try again."
        )

    except aiohttp.ClientError:
        logger.exception("Network error during extraction")
        raise HTTPException(status_code=502, detail="Failed to connect to extraction service")

    except KeyError as e:
        logger.exception("Data parsing error during extraction")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid response structure from extraction service: {str(e)}",
        )

    except Exception as e:
        logger.exception("Unexpected error during extraction")
        raise HTTPException(status_code=500, detail=f"Failed to extract data: {str(e)}")
