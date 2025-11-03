"""
Graph API endpoints for hybrid search and entity operations.

Provides REST API access to:
- Hybrid search (vector + graph)
- Entity connections and traversal
- Entity search
"""

import time
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.hybrid_query import HybridQueryEngine
from app.services.graph_db import GraphDBService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Dependency Injection
# ============================================================================


# Global service instances
_hybrid_query_engine: Optional[HybridQueryEngine] = None
_graph_db_service: Optional[GraphDBService] = None


def get_hybrid_query_engine() -> HybridQueryEngine:
    """Get HybridQueryEngine instance (dependency injection)."""
    if _hybrid_query_engine is None:
        raise RuntimeError("HybridQueryEngine not initialized")
    return _hybrid_query_engine


def set_hybrid_query_engine(engine: HybridQueryEngine):
    """Set HybridQueryEngine instance."""
    global _hybrid_query_engine
    _hybrid_query_engine = engine


def get_graph_db_service() -> GraphDBService:
    """Get GraphDBService instance (dependency injection)."""
    if _graph_db_service is None:
        raise RuntimeError("GraphDBService not initialized")
    return _graph_db_service


def set_graph_db_service(service: GraphDBService):
    """Set GraphDBService instance."""
    global _graph_db_service
    _graph_db_service = service


# ============================================================================
# Pydantic Models
# ============================================================================


class GraphSearchRequest(BaseModel):
    """Request model for hybrid graph search."""

    query: str = Field(..., min_length=1, description="Search query")
    vector_limit: int = Field(default=5, ge=1, le=50, description="Max vector search results")
    graph_depth: int = Field(default=2, ge=1, le=4, description="Graph traversal depth")
    rerank: bool = Field(default=True, description="Enable result reranking")


class GraphSearchResponse(BaseModel):
    """Response model for hybrid graph search."""

    results: List[Dict[str, Any]] = Field(description="Combined search results")
    total: int = Field(description="Total number of results")
    execution_time_ms: float = Field(description="Query execution time in milliseconds")
    retrieval_strategy: str = Field(description="Strategy used: hybrid, vector, or graph")


class EntityConnectionsResponse(BaseModel):
    """Response model for entity connections."""

    entity_id: str = Field(description="ID of the queried entity")
    connections: List[Dict[str, Any]] = Field(description="Connected entities")
    depth: int = Field(description="Traversal depth used")
    total: int = Field(description="Total number of connections found")


class EntitySearchResponse(BaseModel):
    """Response model for entity search."""

    entities: List[Dict[str, Any]] = Field(description="Found entities")
    total: int = Field(description="Total number of entities found")
    query: str = Field(description="Search query used")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/search", response_model=GraphSearchResponse)
async def graph_search(
    request: GraphSearchRequest, hybrid_engine: HybridQueryEngine = Depends(get_hybrid_query_engine)
):
    """
    Perform hybrid search combining vector and graph retrieval.

    This endpoint orchestrates:
    1. Entity extraction from query
    2. Vector search in Qdrant
    3. Graph traversal in Neo4j (if entities found)
    4. Result combination and deduplication
    5. Optional reranking by hybrid score

    Args:
        request: Search parameters
        hybrid_engine: Injected HybridQueryEngine service

    Returns:
        Combined search results with execution metrics

    Raises:
        HTTPException 400: Invalid query (empty or too short)
        HTTPException 500: Service error during search

    Example:
        POST /api/v1/graph/search
        {
            "query": "What projects did Alice work on?",
            "vector_limit": 5,
            "graph_depth": 2,
            "rerank": true
        }
    """
    # Validate query
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Measure execution time
        start_time = time.time()

        # Perform hybrid search
        result = await hybrid_engine.hybrid_search(
            query=request.query,
            vector_limit=request.vector_limit,
            graph_depth=request.graph_depth,
            rerank=request.rerank,
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # Extract combined results
        combined_results = result.get("combined_results", [])
        retrieval_strategy = result.get("retrieval_strategy", "unknown")

        logger.info(
            f"Graph search completed: query='{request.query}', "
            f"results={len(combined_results)}, time={execution_time_ms:.2f}ms, "
            f"strategy={retrieval_strategy}"
        )

        return GraphSearchResponse(
            results=combined_results,
            total=len(combined_results),
            execution_time_ms=execution_time_ms,
            retrieval_strategy=retrieval_strategy,
        )

    except Exception as e:
        logger.error(f"Graph search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/entities/{entity_id}/connections", response_model=EntityConnectionsResponse)
async def get_entity_connections(
    entity_id: str,
    max_depth: int = Query(default=1, ge=1, le=4, description="Graph traversal depth"),
    relationship_types: Optional[str] = Query(
        default=None,
        description="Comma-separated list of relationship types to filter (e.g., 'WORKS_AT,LOCATED_IN')",
    ),
    graph_db: GraphDBService = Depends(get_graph_db_service),
):
    """
    Get entities connected to a specific entity via graph traversal.

    Args:
        entity_id: ID of the entity to query
        max_depth: Maximum graph traversal depth (1-4)
        relationship_types: Optional comma-separated relationship type filters
        graph_db: Injected GraphDBService

    Returns:
        Connected entities with metadata

    Raises:
        HTTPException 404: Entity not found
        HTTPException 500: Service error during traversal

    Example:
        GET /api/v1/graph/entities/PERSON_Alice_Smith/connections?max_depth=2&relationship_types=WORKS_AT
    """
    try:
        # Check if entity exists
        entity = await graph_db.get_entity_by_id(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

        # Parse relationship types filter
        rel_types_list: Optional[List[str]] = None
        if relationship_types:
            rel_types_list = [rt.strip() for rt in relationship_types.split(",")]

        # Find connected entities
        connections = await graph_db.find_connected_entities(
            entity_id=entity_id, max_depth=max_depth, relationship_types=rel_types_list
        )

        logger.info(
            f"Found {len(connections)} connections for entity '{entity_id}' "
            f"(depth={max_depth}, filters={rel_types_list})"
        )

        return EntityConnectionsResponse(
            entity_id=entity_id, connections=connections, depth=max_depth, total=len(connections)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connections for entity '{entity_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {str(e)}")


@router.get("/entities/search", response_model=EntitySearchResponse)
async def search_entities(
    query: str = Query(..., min_length=1, description="Search query"),
    entity_types: Optional[str] = Query(
        default=None,
        description="Comma-separated list of entity types to filter (e.g., 'PERSON,ORG')",
    ),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of results"),
    graph_db: GraphDBService = Depends(get_graph_db_service),
):
    """
    Search for entities by text.

    Args:
        query: Text to search for in entity names
        entity_types: Optional comma-separated entity type filters
        limit: Maximum results (1-100)
        graph_db: Injected GraphDBService

    Returns:
        Matching entities

    Raises:
        HTTPException 500: Service error during search

    Example:
        GET /api/v1/graph/entities/search?query=Alice&entity_types=PERSON&limit=10
    """
    try:
        # Parse entity types filter
        types_list: Optional[List[str]] = None
        if entity_types:
            types_list = [et.strip() for et in entity_types.split(",")]

        # Search entities
        entities = await graph_db.search_entities(query=query, entity_types=types_list, limit=limit)

        logger.info(
            f"Entity search: query='{query}', types={types_list}, "
            f"limit={limit}, found={len(entities)}"
        )

        return EntitySearchResponse(entities=entities, total=len(entities), query=query)

    except Exception as e:
        logger.error(f"Entity search error for query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
