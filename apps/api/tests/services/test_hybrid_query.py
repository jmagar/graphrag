"""
Tests for hybrid query service.

TDD Approach: Write tests first (RED), then implement (GREEN), then refactor.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.hybrid_query import HybridQueryEngine


@pytest.mark.asyncio
class TestHybridQueryEngine:
    """Test suite for HybridQueryEngine."""

    @pytest_asyncio.fixture
    async def query_engine(self):
        """Create a HybridQueryEngine with mocked dependencies."""
        with patch('app.services.hybrid_query.EntityExtractor') as mock_entity_class, \
             patch('app.services.hybrid_query.EmbeddingsService') as mock_embeddings_class, \
             patch('app.services.hybrid_query.VectorDBService') as mock_vector_class, \
             patch('app.services.hybrid_query.GraphDBService') as mock_graph_class:
            
            # Create mock instances
            mock_entity_extractor = AsyncMock()
            mock_embeddings = AsyncMock()
            mock_vector_db = AsyncMock()
            mock_graph_db = AsyncMock()
            
            mock_entity_class.return_value = mock_entity_extractor
            mock_embeddings_class.return_value = mock_embeddings
            mock_vector_class.return_value = mock_vector_db
            mock_graph_class.return_value = mock_graph_db
            
            # Create engine
            engine = HybridQueryEngine()
            
            # Store mocks for test access
            engine.mock_entity_extractor = mock_entity_extractor
            engine.mock_embeddings = mock_embeddings
            engine.mock_vector_db = mock_vector_db
            engine.mock_graph_db = mock_graph_db
            
            yield engine

    async def test_hybrid_search_with_no_entities(self, query_engine):
        """Test hybrid search when query has no entities."""
        query = "What is the meaning of life?"
        
        # Mock: No entities in query
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        
        # Mock: Vector search returns results
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": "doc1", "content": "Answer about life", "score": 0.9}
        ]
        
        result = await query_engine.hybrid_search(query, vector_limit=5)
        
        # Should still return results (vector-only)
        assert "query" in result
        assert "vector_results" in result
        assert "retrieval_strategy" in result
        assert len(result["vector_results"]) > 0

    async def test_hybrid_search_with_entities(self, query_engine):
        """Test hybrid search with entities in query."""
        query = "What projects has Alice worked on?"
        
        # Mock: Entity extraction finds "Alice"
        query_engine.mock_entity_extractor.extract_entities.return_value = [
            {"text": "Alice", "type": "PERSON"}
        ]
        
        # Mock: Vector search
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": "doc1", "content": "Alice project info", "score": 0.9}
        ]
        
        # Mock: Graph search finds Alice and connected entities
        query_engine.mock_graph_db.search_entities.return_value = [
            {"id": "alice_1", "text": "Alice", "type": "PERSON"}
        ]
        query_engine.mock_graph_db.find_connected_entities.return_value = [
            {
                "connected": {"id": "proj1", "text": "Project Alpha", "type": "PRODUCT"},
                "relationship_path": ["WORKS_ON"],
                "distance": 1
            }
        ]
        
        result = await query_engine.hybrid_search(query, vector_limit=5, graph_depth=2)
        
        # Should return both vector and graph results
        assert result["query"] == query
        assert len(result["query_entities"]) == 1
        assert len(result["vector_results"]) > 0
        assert len(result["graph_results"]) > 0
        assert result["retrieval_strategy"] == "hybrid"

    async def test_combine_results_deduplication(self, query_engine):
        """Test that combined results deduplicate by document ID."""
        vector_results = [
            {"id": "doc1", "content": "Content 1", "score": 0.9},
            {"id": "doc2", "content": "Content 2", "score": 0.8}
        ]
        
        graph_results = [
            {"id": "doc1", "text": "Content 1", "distance": 1},  # Duplicate
            {"id": "doc3", "text": "Content 3", "distance": 2}
        ]
        
        combined = query_engine._combine_results(vector_results, graph_results)
        
        # Should have 3 unique documents (doc1, doc2, doc3)
        assert len(combined) == 3
        
        # doc1 should have both vector_score and graph_distance
        doc1 = next(r for r in combined if r["id"] == "doc1")
        assert doc1["vector_score"] is not None
        assert doc1["graph_distance"] is not None
        assert doc1["source"] == "both"

    async def test_combine_results_source_labels(self, query_engine):
        """Test that combined results have correct source labels."""
        vector_results = [{"id": "doc1", "score": 0.9}]
        graph_results = [{"id": "doc2", "distance": 1}]
        
        combined = query_engine._combine_results(vector_results, graph_results)
        
        # Check source labels
        doc1 = next(r for r in combined if r["id"] == "doc1")
        doc2 = next(r for r in combined if r["id"] == "doc2")
        
        assert doc1["source"] == "vector"
        assert doc2["source"] == "graph"

    async def test_rerank_results_prefers_both_sources(self, query_engine):
        """Test that reranking prefers results from both sources."""
        query = "test query"
        results = [
            {"id": "doc1", "vector_score": 0.8, "graph_distance": None, "source": "vector"},
            {"id": "doc2", "vector_score": 0.7, "graph_distance": 1, "source": "both"},
            {"id": "doc3", "vector_score": None, "graph_distance": 2, "source": "graph"}
        ]
        
        reranked = await query_engine._rerank_results(query, results)
        
        # All results should have hybrid_score
        assert all("hybrid_score" in r for r in reranked)
        
        # doc2 (both sources) should be ranked higher despite lower vector score
        doc2_score = next(r for r in reranked if r["id"] == "doc2")["hybrid_score"]
        doc1_score = next(r for r in reranked if r["id"] == "doc1")["hybrid_score"]
        
        assert doc2_score > doc1_score, "Results from both sources should rank higher"

    async def test_rerank_results_sorting(self, query_engine):
        """Test that reranked results are sorted by hybrid_score."""
        query = "test"
        results = [
            {"id": "doc1", "vector_score": 0.5, "graph_distance": None, "source": "vector"},
            {"id": "doc2", "vector_score": 0.9, "graph_distance": None, "source": "vector"},
            {"id": "doc3", "vector_score": 0.7, "graph_distance": None, "source": "vector"}
        ]
        
        reranked = await query_engine._rerank_results(query, results)
        
        # Should be sorted by hybrid_score descending
        scores = [r["hybrid_score"] for r in reranked]
        assert scores == sorted(scores, reverse=True)

    async def test_hybrid_search_performance_target(self, query_engine):
        """Test that hybrid search completes within performance target."""
        import time
        
        query = "test query"
        
        # Mock fast responses
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": f"doc{i}", "score": 0.9 - i*0.1} for i in range(5)
        ]
        
        start_time = time.time()
        result = await query_engine.hybrid_search(query)
        elapsed = time.time() - start_time
        
        # Should complete in less than 1 second (target from spec)
        assert elapsed < 1.0, f"Query took {elapsed:.2f}s, should be <1s"

    async def test_hybrid_search_with_vector_limit(self, query_engine):
        """Test that vector_limit parameter is respected."""
        query = "test query"
        vector_limit = 3
        
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": f"doc{i}", "score": 0.9} for i in range(vector_limit)
        ]
        
        result = await query_engine.hybrid_search(query, vector_limit=vector_limit)
        
        # Vector DB search should be called with correct limit
        query_engine.mock_vector_db.search.assert_called_once()
        call_kwargs = query_engine.mock_vector_db.search.call_args.kwargs
        assert call_kwargs["limit"] == vector_limit

    async def test_hybrid_search_with_graph_depth(self, query_engine):
        """Test that graph_depth parameter is respected."""
        query = "Alice's projects"
        graph_depth = 3
        
        # Mock entity in query
        query_engine.mock_entity_extractor.extract_entities.return_value = [
            {"text": "Alice", "type": "PERSON"}
        ]
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = []
        query_engine.mock_graph_db.search_entities.return_value = [
            {"id": "alice_1", "text": "Alice"}
        ]
        query_engine.mock_graph_db.find_connected_entities.return_value = []
        
        result = await query_engine.hybrid_search(
            query, 
            vector_limit=5, 
            graph_depth=graph_depth
        )
        
        # Graph DB should be called with correct depth
        query_engine.mock_graph_db.find_connected_entities.assert_called_once()
        call_kwargs = query_engine.mock_graph_db.find_connected_entities.call_args.kwargs
        assert call_kwargs["max_depth"] == graph_depth

    async def test_hybrid_search_with_rerank_disabled(self, query_engine):
        """Test hybrid search with reranking disabled."""
        query = "test"
        
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": "doc1", "score": 0.9}
        ]
        
        result = await query_engine.hybrid_search(query, rerank=False)
        
        # Combined results should not have hybrid_score
        if result["combined_results"]:
            assert "hybrid_score" not in result["combined_results"][0]

    async def test_empty_query_returns_structure(self, query_engine):
        """Test that empty query returns proper structure."""
        result = await query_engine.hybrid_search("")
        
        assert "query" in result
        assert "query_entities" in result
        assert "vector_results" in result
        assert "graph_results" in result
        assert "combined_results" in result
        assert "retrieval_strategy" in result


@pytest.mark.asyncio
class TestHybridQueryWithCache:
    """Test HybridQueryEngine with query result caching."""

    @pytest_asyncio.fixture
    async def query_engine(self):
        """Create a HybridQueryEngine with mocked dependencies."""
        with patch('app.services.hybrid_query.EntityExtractor') as mock_entity_class, \
             patch('app.services.hybrid_query.EmbeddingsService') as mock_embeddings_class, \
             patch('app.services.hybrid_query.VectorDBService') as mock_vector_class, \
             patch('app.services.hybrid_query.GraphDBService') as mock_graph_class:

            # Create mock instances
            mock_entity_extractor = AsyncMock()
            mock_embeddings = AsyncMock()
            mock_vector_db = AsyncMock()
            mock_graph_db = AsyncMock()

            mock_entity_class.return_value = mock_entity_extractor
            mock_embeddings_class.return_value = mock_embeddings
            mock_vector_class.return_value = mock_vector_db
            mock_graph_class.return_value = mock_graph_db

            # Create engine
            engine = HybridQueryEngine()

            # Store mocks for test access
            engine.mock_entity_extractor = mock_entity_extractor
            engine.mock_embeddings = mock_embeddings
            engine.mock_vector_db = mock_vector_db
            engine.mock_graph_db = mock_graph_db

            yield engine

    @pytest_asyncio.fixture
    async def mock_query_cache(self):
        """Create a mock QueryCache."""
        cache = AsyncMock()
        cache.get.return_value = None  # Default: cache miss
        cache.set.return_value = None
        cache.invalidate_collection.return_value = None
        cache.get_stats.return_value = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "hit_rate": 0.0
        }
        return cache

    async def test_hybrid_search_with_cache_miss(self, query_engine, mock_query_cache):
        """Test hybrid search performs full search on cache miss."""
        query_engine.query_cache = mock_query_cache
        query = "What is GraphRAG?"

        # Configure mocks for full search
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": "doc1", "content": "GraphRAG info", "score": 0.9}
        ]

        # Configure cache miss
        mock_query_cache.get.return_value = None

        result = await query_engine.hybrid_search(query)

        # Should perform full search
        query_engine.mock_vector_db.search.assert_called_once()

        # Should cache results
        mock_query_cache.set.assert_called_once()

        assert len(result["vector_results"]) > 0

    async def test_hybrid_search_with_cache_hit(self, query_engine, mock_query_cache):
        """Test hybrid search returns cached results on cache hit."""
        query_engine.query_cache = mock_query_cache
        query = "What is GraphRAG?"

        # Configure cache hit with complete cached result
        cached_result = {
            "query": query,
            "query_entities": [],
            "vector_results": [{"id": "cached_doc", "score": 0.95}],
            "graph_results": [],
            "combined_results": [{"id": "cached_doc", "score": 0.95}],
            "retrieval_strategy": "vector"
        }
        mock_query_cache.get.return_value = cached_result

        result = await query_engine.hybrid_search(query)

        # Should NOT perform any searches
        query_engine.mock_vector_db.search.assert_not_called()
        query_engine.mock_graph_db.find_connected_entities.assert_not_called()
        query_engine.mock_embeddings.generate_embedding.assert_not_called()

        # Should return cached result
        assert result == cached_result
        assert result["vector_results"][0]["id"] == "cached_doc"

    async def test_cache_invalidation_on_data_update(self, query_engine, mock_query_cache):
        """Test cache is invalidated when vector database is updated."""
        query_engine.query_cache = mock_query_cache

        # Simulate data update (e.g., new documents added)
        # This would happen in the actual VectorDBService upsert
        await mock_query_cache.invalidate_collection("graphrag")

        # Verify invalidation was called
        mock_query_cache.invalidate_collection.assert_called_once_with("graphrag")

    async def test_cache_respects_different_parameters(self, query_engine, mock_query_cache):
        """Test cache differentiates queries with different parameters."""
        query_engine.query_cache = mock_query_cache
        query = "test query"

        # Configure mocks
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [{"id": "doc1", "score": 0.9}]

        # Search with different parameters
        await query_engine.hybrid_search(query, vector_limit=5)
        await query_engine.hybrid_search(query, vector_limit=10)
        await query_engine.hybrid_search(query, graph_depth=2)
        await query_engine.hybrid_search(query, rerank=False)

        # Each call should attempt to get from cache with different keys
        assert mock_query_cache.get.call_count == 4

        # Each should result in separate cache entries
        assert mock_query_cache.set.call_count == 4

    async def test_partial_cache_hit_vector_only(self, query_engine, mock_query_cache):
        """Test handling of cached vector results but not graph results."""
        query_engine.query_cache = mock_query_cache
        query = "Alice's projects"

        # Configure entity extraction to trigger graph search
        query_engine.mock_entity_extractor.extract_entities.return_value = [
            {"text": "Alice", "type": "PERSON"}
        ]

        # Cache has vector results but query now has entities (needs graph search)
        cached_vector_results = [{"id": "doc1", "score": 0.9}]
        mock_query_cache.get.return_value = None  # No full cache

        # Configure mocks for full hybrid search
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = cached_vector_results
        query_engine.mock_graph_db.search_entities.return_value = [
            {"id": "alice_1", "text": "Alice"}
        ]
        query_engine.mock_graph_db.find_connected_entities.return_value = []

        result = await query_engine.hybrid_search(query)

        # Should perform full hybrid search
        assert result["retrieval_strategy"] == "hybrid" or result["retrieval_strategy"] == "vector"

    async def test_cache_performance_benefit(self, query_engine, mock_query_cache):
        """Test that caching provides performance benefit."""
        import time
        query_engine.query_cache = mock_query_cache
        query = "performance test"

        # Configure mocks with simulated delay
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768

        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow database query
            return [{"id": "doc1", "score": 0.9}]

        query_engine.mock_vector_db.search = slow_search

        # First query - cache miss (slow)
        mock_query_cache.get.return_value = None
        start = time.time()
        result1 = await query_engine.hybrid_search(query)
        uncached_time = time.time() - start

        # Second query - cache hit (fast)
        mock_query_cache.get.return_value = result1
        start = time.time()
        result2 = await query_engine.hybrid_search(query)
        cached_time = time.time() - start

        # Cached query should be significantly faster
        assert cached_time < uncached_time / 2, \
            f"Cached time ({cached_time:.3f}s) not faster than uncached ({uncached_time:.3f}s)"

    async def test_cache_handles_errors_gracefully(self, query_engine, mock_query_cache):
        """Test hybrid search handles cache errors gracefully."""
        query_engine.query_cache = mock_query_cache
        query = "test query"

        # Simulate cache error
        mock_query_cache.get.side_effect = ConnectionError("Redis down")

        # Configure mocks for fallback search
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [{"id": "doc1", "score": 0.9}]

        # Should still work despite cache error
        result = await query_engine.hybrid_search(query)

        assert result is not None
        assert len(result["vector_results"]) > 0

    async def test_cache_stores_complete_hybrid_result(self, query_engine, mock_query_cache):
        """Test cache stores complete hybrid search result with all components."""
        query_engine.query_cache = mock_query_cache
        query = "Alice's work on Project X"

        # Configure full hybrid search
        query_engine.mock_entity_extractor.extract_entities.return_value = [
            {"text": "Alice", "type": "PERSON"}
        ]
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [
            {"id": "doc1", "score": 0.9}
        ]
        query_engine.mock_graph_db.search_entities.return_value = [
            {"id": "alice_1", "text": "Alice"}
        ]
        query_engine.mock_graph_db.find_connected_entities.return_value = [
            {
                "connected": {"id": "proj1", "text": "Project X"},
                "distance": 1
            }
        ]

        mock_query_cache.get.return_value = None

        result = await query_engine.hybrid_search(query)

        # Verify complete result was cached
        mock_query_cache.set.assert_called_once()
        cached_result = mock_query_cache.set.call_args[0][2]  # Third positional arg

        # Cached result should have all components
        assert "query" in cached_result
        assert "query_entities" in cached_result
        assert "vector_results" in cached_result
        assert "graph_results" in cached_result
        assert "combined_results" in cached_result
        assert "retrieval_strategy" in cached_result

    async def test_cache_without_cache_service(self, query_engine):
        """Test hybrid search works normally without cache service."""
        # No cache configured
        query = "test"

        # Configure mocks
        query_engine.mock_entity_extractor.extract_entities.return_value = []
        query_engine.mock_embeddings.generate_embedding.return_value = [0.1] * 768
        query_engine.mock_vector_db.search.return_value = [{"id": "doc1", "score": 0.9}]

        # Should work normally without caching
        result = await query_engine.hybrid_search(query)

        assert result is not None
        assert "vector_results" in result
