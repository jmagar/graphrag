"""
Hybrid query service combining vector search and graph traversal.

Orchestrates retrieval across both vector database (Qdrant) and graph database (Neo4j)
to provide enhanced context for RAG queries.
"""

import logging
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from app.services.entity_extractor import EntityExtractor
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
from app.services.graph_db import GraphDBService

if TYPE_CHECKING:
    from app.services.query_cache import QueryCache

logger = logging.getLogger(__name__)


class HybridQueryEngine:
    """Orchestrate hybrid queries across vector and graph databases."""

    def __init__(self, query_cache: Optional["QueryCache"] = None):
        """
        Initialize the hybrid query engine with all required services.

        Args:
            query_cache: Optional QueryCache instance for caching hybrid query results
        """
        self.entity_extractor = EntityExtractor()
        self.embeddings_service = EmbeddingsService()
        self.vector_db_service = VectorDBService(query_cache=query_cache)
        self.graph_db_service = GraphDBService()
        self.query_cache = query_cache
        logger.info("Initialized HybridQueryEngine")

    async def hybrid_search(
        self, query: str, vector_limit: int = 5, graph_depth: int = 2, rerank: bool = True
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector and graph retrieval.

        Args:
            query: User's search query
            vector_limit: Maximum number of vector search results
            graph_depth: Maximum graph traversal depth (1-4 recommended)
            rerank: Whether to rerank combined results

        Returns:
            Dictionary containing:
            - query: Original query
            - query_entities: Entities extracted from query
            - vector_results: Results from vector search
            - graph_results: Results from graph search
            - combined_results: Merged and deduplicated results
            - retrieval_strategy: "hybrid", "vector", or "graph"

        Example:
            >>> engine = HybridQueryEngine()
            >>> results = await engine.hybrid_search(
            ...     "What projects has Alice worked on?",
            ...     vector_limit=5,
            ...     graph_depth=2
            ... )
        """
        # Handle empty query
        if not query or not query.strip():
            return {
                "query": query,
                "query_entities": [],
                "vector_results": [],
                "graph_results": [],
                "combined_results": [],
                "retrieval_strategy": "none",
            }

        # Try to get cached hybrid search results
        if self.query_cache:
            cached_results = await self.query_cache.get(
                collection="hybrid",
                query_text=query,
                vector_limit=vector_limit,
                graph_depth=graph_depth,
                rerank=rerank,
            )
            if cached_results is not None:
                logger.debug(f"Returning cached hybrid results for query: {query[:50]}...")
                return cached_results

        # Cache miss or caching disabled - perform hybrid search
        start_time = time.time()

        # Step 1: Extract entities from query
        query_entities = await self.entity_extractor.extract_entities(query)
        logger.debug(f"Extracted {len(query_entities)} entities from query")

        # Step 2: Vector search (always performed)
        query_embedding = await self.embeddings_service.generate_embedding(query)
        vector_results = await self.vector_db_service.search(
            query_embedding=query_embedding, limit=vector_limit, query_text=query
        )
        logger.debug(f"Vector search found {len(vector_results)} results")

        # Step 3: Graph search (only if entities found in query)
        graph_results = []
        if query_entities:
            graph_results = await self._graph_search(
                query_entities=query_entities, max_depth=graph_depth
            )
            logger.debug(f"Graph search found {len(graph_results)} results")

        # Step 4: Combine results
        combined_results = self._combine_results(
            vector_results=vector_results, graph_results=graph_results
        )
        logger.debug(f"Combined into {len(combined_results)} unique results")

        # Step 5: Rerank (optional)
        if rerank and combined_results:
            combined_results = await self._rerank_results(query, combined_results)
            logger.debug("Reranked combined results")

        # Determine retrieval strategy
        strategy = "hybrid"
        if not graph_results:
            strategy = "vector"
        elif not vector_results:
            strategy = "graph"

        result = {
            "query": query,
            "query_entities": query_entities,
            "vector_results": vector_results,
            "graph_results": graph_results,
            "combined_results": combined_results,
            "retrieval_strategy": strategy,
        }

        # Cache hybrid search results
        if self.query_cache:
            query_time_ms = (time.time() - start_time) * 1000
            await self.query_cache.set(
                collection="hybrid",
                query_text=query,
                results=result,
                query_time_ms=query_time_ms,
                vector_limit=vector_limit,
                graph_depth=graph_depth,
                rerank=rerank,
            )

        return result

    async def _graph_search(
        self, query_entities: List[Dict[str, Any]], max_depth: int
    ) -> List[Dict[str, Any]]:
        """
        Search graph database for connected entities.

        Args:
            query_entities: Entities extracted from query
            max_depth: Maximum traversal depth

        Returns:
            List of connected entities with metadata
        """
        all_connected = []

        for entity in query_entities:
            entity_text = entity["text"]

            # Find entity in graph
            entity_nodes = await self.graph_db_service.search_entities(query=entity_text, limit=1)

            if not entity_nodes:
                continue

            # Get connected entities via graph traversal
            entity_id = entity_nodes[0]["id"]
            connected = await self.graph_db_service.find_connected_entities(
                entity_id=entity_id, max_depth=max_depth
            )

            all_connected.extend(connected)

        return all_connected

    def _combine_results(
        self, vector_results: List[Dict[str, Any]], graph_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine and deduplicate results from vector and graph search.

        Args:
            vector_results: Results from vector search
            graph_results: Results from graph search

        Returns:
            List of combined unique results with source labels
        """
        results_map: Dict[str, Dict[str, Any]] = {}

        # Add vector results
        for result in vector_results:
            doc_id = result.get("id")
            if not doc_id:
                continue

            results_map[doc_id] = {
                **result,
                "vector_score": result.get("score"),
                "graph_distance": None,
                "source": "vector",
            }

        # Add graph results
        for result in graph_results:
            # Handle both formats: direct dict or nested connected entity
            if "connected" in result:
                # Format from find_connected_entities
                connected = result.get("connected", {})
                doc_id = connected.get("id")
                distance = result.get("distance")
                entity_data = connected
            else:
                # Direct format (for test compatibility)
                doc_id = result.get("id")
                distance = result.get("distance")
                entity_data = result

            if not doc_id:
                continue

            if doc_id in results_map:
                # Enhance existing result with graph data
                results_map[doc_id]["graph_distance"] = distance
                results_map[doc_id]["source"] = "both"
            else:
                # Add new graph-only result
                results_map[doc_id] = {
                    "id": doc_id,
                    **entity_data,
                    "vector_score": None,
                    "graph_distance": distance,
                    "source": "graph",
                }

        return list(results_map.values())

    async def _rerank_results(
        self, query: str, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank combined results using a hybrid scoring function.

        Args:
            query: Original query (for context)
            results: Combined results to rerank

        Returns:
            Reranked results sorted by hybrid_score
        """
        for result in results:
            score = 0.0

            # Vector score contribution (60% weight)
            if result.get("vector_score") is not None:
                score += result["vector_score"] * 0.6

            # Graph distance contribution (40% weight)
            # Closer entities (lower distance) get higher scores
            if result.get("graph_distance") is not None:
                distance = result["graph_distance"]
                # Inverse distance: 1 hop = 1.0, 2 hops = 0.5, 3 hops = 0.33, etc.
                graph_score = 1.0 / distance if distance > 0 else 1.0
                score += graph_score * 0.4

            # Bonus for appearing in both sources (20% boost)
            if result.get("source") == "both":
                score *= 1.2

            result["hybrid_score"] = score

        # Sort by hybrid score descending
        results.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)

        return results
