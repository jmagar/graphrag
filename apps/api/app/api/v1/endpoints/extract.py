"""
Extract endpoint for structured data extraction using Firecrawl v2 API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
from app.services.firecrawl import FirecrawlService

router = APIRouter()
firecrawl_service = FirecrawlService()


class ExtractRequest(BaseModel):
    """Request model for extracting structured data."""

    url: HttpUrl
    schema: Dict[str, Any]
    formats: Optional[List[str]] = ["markdown"]


class ExtractResponse(BaseModel):
    """Response model for extract."""

    success: bool
    data: Dict[str, Any]


@router.post("/", response_model=ExtractResponse)
async def extract_data(request: ExtractRequest):
    """
    Extract structured data from a webpage.

    Uses natural language or JSON schema to extract specific data.
    """
    try:
        options = {}
        if request.formats:
            options["formats"] = request.formats

        result = await firecrawl_service.extract_data(str(request.url), request.schema, options)

        return {"success": True, "data": result.get("data", {})}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract data: {str(e)}")
