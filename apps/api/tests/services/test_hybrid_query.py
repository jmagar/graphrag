"""
Tests for hybrid query service.

TDD Approach: Write tests first (RED), then implement (GREEN), then refactor.
"""

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
