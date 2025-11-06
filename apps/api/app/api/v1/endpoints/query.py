"""
RAG query endpoints for semantic search and LLM-powered responses.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional
from httpx import TimeoutException, HTTPStatusError, ConnectError
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
from app.services.llm import LLMService
from app.dependencies import get_embeddings_service, get_vector_db_service, get_llm_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


class QueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str = Field(..., min_length=1, max_length=10000, description="Query text (1-10000 characters)")
    limit: int = Field(5, ge=1, le=100, description="Maximum number of results (1-100)")
    score_threshold: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score (0.0-1.0)")
    use_llm: bool = True
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Individual search result."""

    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class QueryResponse(BaseModel):
    """Response model for RAG queries."""

    query: str
    results: List[SearchResult]
    llm_response: Optional[str] = None
    total_results: int


@router.post("/", response_model=QueryResponse)
@limiter.limit("100/minute")
async def query_knowledge_base(
    http_request: Request,
    request: QueryRequest,
    embeddings: EmbeddingsService = Depends(get_embeddings_service),
    vector_db: VectorDBService = Depends(get_vector_db_service),
    llm: LLMService = Depends(get_llm_service),
):
    """
    Query the knowledge base using semantic search and optional LLM generation.

    Steps:
    1. Generate embedding for the query
    2. Search vector database for relevant documents
    3. (Optional) Use LLM to generate a response based on retrieved context

    Rate limit: 100 requests per minute per IP address
    """
    try:
        # Generate query embedding
        query_embedding = await embeddings.generate_embedding(request.query)

        # Search vector database (with caching)
        search_results = await vector_db.search(
            query_embedding=query_embedding,
            limit=request.limit,
            score_threshold=request.score_threshold,
            filters=request.filters,
            query_text=request.query,  # Pass query text for cache key generation
        )

        # Convert to response format
        results = [
            SearchResult(
                id=str(result["id"]),
                score=result["score"],
                content=result["content"][:500],  # Truncate for response
                metadata=result["metadata"],
            )
            for result in search_results
        ]

        # Generate LLM response if requested
        llm_response = None
        if request.use_llm and search_results:
            context = "\n\n".join(
                [
                    f"[Source: {r['metadata'].get('sourceURL', 'Unknown')}]\n{r['content']}"
                    for r in search_results[:3]
                ]
            )
            llm_response = await llm.generate_response(
                query=request.query,
                context=context,
            )

        return QueryResponse(
            query=request.query,
            results=results,
            llm_response=llm_response,
            total_results=len(results),
        )

    except ValidationError as e:
        logger.exception("Validation error during query")
        raise HTTPException(status_code=422, detail=f"Invalid query request: {str(e)}")

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error during query")
        raise HTTPException(
            status_code=504, detail="Query timed out. Please try again with a shorter query or fewer results."
        )

    except (ConnectError, HTTPStatusError) as e:
        logger.exception("Service connection error during query")
        service_name = "embeddings or vector database"
        if "ollama" in str(e).lower():
            service_name = "LLM"
        raise HTTPException(
            status_code=503,
            detail=f"{service_name} service unavailable: {str(e)}"
        )

    except ValueError as e:
        logger.exception("Value error during query processing")
        raise HTTPException(status_code=400, detail=f"Invalid query parameters: {str(e)}")

    except KeyError as e:
        logger.exception("Data access error during query")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid data structure: missing field {str(e)}",
        )

    except Exception as e:
        logger.exception("Unexpected error during query")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/collection/info")
async def get_collection_info(vector_db: VectorDBService = Depends(get_vector_db_service)):
    """Get information about the vector database collection."""
    try:
        info = await vector_db.get_collection_info()
        return info

    except (TimeoutException, asyncio.TimeoutError):
        logger.exception("Timeout error fetching collection info")
        raise HTTPException(
            status_code=504, detail="Request timed out. Please try again."
        )

    except ConnectError:
        logger.exception("Connection error fetching collection info")
        raise HTTPException(status_code=503, detail="Vector database service unavailable")

    except Exception as e:
        logger.exception("Unexpected error fetching collection info")
        raise HTTPException(status_code=500, detail=f"Failed to get collection info: {str(e)}")
