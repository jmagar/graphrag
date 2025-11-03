"""
RAG query endpoints for semantic search and LLM-powered responses.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
from app.services.llm import LLMService
from app.dependencies import get_embeddings_service, get_vector_db_service, get_llm_service

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str
    limit: int = 5
    score_threshold: Optional[float] = 0.5
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
async def query_knowledge_base(
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
    """
    try:
        # Generate query embedding
        query_embedding = await embeddings.generate_embedding(request.query)

        # Search vector database
        search_results = await vector_db.search(
            query_embedding=query_embedding,
            limit=request.limit,
            score_threshold=request.score_threshold,
            filters=request.filters,
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/collection/info")
async def get_collection_info(vector_db: VectorDBService = Depends(get_vector_db_service)):
    """Get information about the vector database collection."""
    try:
        info = await vector_db.get_collection_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection info: {str(e)}")
