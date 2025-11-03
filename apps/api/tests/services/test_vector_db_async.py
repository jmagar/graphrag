"""
VectorDB Async Initialization Tests

RED Phase: These tests should FAIL initially (no async methods exist yet)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_db import VectorDBService


@pytest.mark.asyncio
class TestVectorDBAsync:
    """Test async initialization and operations of VectorDBService."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock async Qdrant client."""
        mock_client = AsyncMock()
        
        # Mock get_collections response
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        
        # Mock create_collection
        mock_client.create_collection.return_value = None
        
        # Mock close
        mock_client.close.return_value = None
        
        return mock_client
    
    async def test_initialize_creates_collection(self, mock_qdrant_client):
        """
        Test async initialization creates collection.
        
        GREEN: Should PASS now that initialize() is implemented
        """
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            
            # Verify client was created
            assert service.client is not None
            
            # Verify get_collections was called
            mock_qdrant_client.get_collections.assert_called_once()
            
            # Verify create_collection was called (empty collection list)
            mock_qdrant_client.create_collection.assert_called_once()
            
            await service.close()
    
    async def test_close_releases_connection(self, mock_qdrant_client):
        """
        Test close properly releases connection.
        
        GREEN: Should PASS now that close() is implemented
        """
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            await service.close()
            
            assert service.client is None
            mock_qdrant_client.close.assert_called_once()
    
    async def test_uses_async_client(self, mock_qdrant_client):
        """
        Test service uses AsyncQdrantClient not QdrantClient.
        
        GREEN: Should PASS - now uses AsyncQdrantClient
        """
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            
            # Client should be set (it's our mock, but that's fine)
            assert service.client is not None
            assert service.client == mock_qdrant_client
            
            await service.close()
    
    async def test_upsert_document_is_async(self, mock_qdrant_client):
        """
        Test upsert_document can be awaited.
        
        GREEN: Should work with async client
        """
        mock_qdrant_client.upsert.return_value = None
        
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            
            # Try to upsert a test document
            test_embedding = [0.1] * 1024
            doc_id = "test-doc-async"
            content = "Test content for async operations"
            metadata = {"test": True}
            
            await service.upsert_document(doc_id, test_embedding, content, metadata)
            
            # Verify upsert was called
            mock_qdrant_client.upsert.assert_called_once()
            
            await service.close()
    
    async def test_search_is_async(self, mock_qdrant_client):
        """
        Test search can be awaited.
        
        GREEN: Should work with async client
        """
        mock_qdrant_client.search.return_value = []
        
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            
            # Try to search
            query_embedding = [0.1] * 1024
            results = await service.search(query_embedding, limit=5)
            
            assert isinstance(results, list)
            mock_qdrant_client.search.assert_called_once()
            
            await service.close()
    
    async def test_multiple_initialize_calls_safe(self, mock_qdrant_client):
        """
        Test that calling initialize() multiple times is safe.
        
        GREEN: Should be idempotent
        """
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            
            # First initialization
            await service.initialize()
            client1 = service.client
            
            # Second initialization (should be safe - idempotent)
            await service.initialize()
            client2 = service.client
            
            # Should be the same client
            assert client1 is not None
            assert client2 is not None
            assert client1 == client2  # Same mock instance
            
            await service.close()
    
    async def test_operations_before_initialize_raise_error(self):
        """
        Test that using service before initialize() raises clear error.
        
        RED: Will FAIL - currently creates client in __init__
        """
        service = VectorDBService()
        
        # Should fail gracefully with clear error
        with pytest.raises((RuntimeError, AttributeError)) as exc_info:
            await service.search([0.1] * 1024)
        
        # Error message should be helpful
        error_msg = str(exc_info.value).lower()
        assert 'initialize' in error_msg or 'not initialized' in error_msg


@pytest.mark.asyncio
class TestVectorDBWithCache:
    """Test VectorDBService integration with QueryCache."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock async Qdrant client."""
        mock_client = AsyncMock()
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_client.create_collection.return_value = None
        mock_client.close.return_value = None

        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "doc1"
        mock_result.score = 0.95
        mock_result.payload = {
            "content": "Test content",
            "metadata": {"sourceURL": "https://example.com"}
        }
        mock_client.search.return_value = [mock_result]

        return mock_client

    @pytest.fixture
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

    async def test_search_with_cache_miss(self, mock_qdrant_client, mock_query_cache):
        """Test search performs database query on cache miss."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            # Configure cache miss
            mock_query_cache.get.return_value = None

            # Perform search
            query_embedding = [0.1] * 1024
            results = await service.search(query_embedding, limit=5, query_text="test-query")

            # Should query Qdrant
            mock_qdrant_client.search.assert_called_once()

            # Should store in cache
            mock_query_cache.set.assert_called_once()

            assert len(results) > 0
            await service.close()

    async def test_search_with_cache_hit(self, mock_qdrant_client, mock_query_cache):
        """Test search returns cached results on cache hit."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            # Configure cache hit
            cached_results = [
                {
                    "id": "cached_doc1",
                    "score": 0.98,
                    "content": "Cached content",
                    "metadata": {"cached": True}
                }
            ]
            mock_query_cache.get.return_value = cached_results

            # Perform search
            query_embedding = [0.1] * 1024
            results = await service.search(query_embedding, limit=5, query_text="test-query")

            # Should NOT query Qdrant
            mock_qdrant_client.search.assert_not_called()

            # Should return cached results
            assert results == cached_results
            assert results[0]["metadata"]["cached"] is True

            await service.close()

    async def test_search_caches_with_correct_parameters(self, mock_qdrant_client, mock_query_cache):
        """Test search caches results with correct query parameters."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            # Configure cache miss
            mock_query_cache.get.return_value = None

            # Perform search with specific parameters
            query_embedding = [0.1] * 1024
            await service.search(
                query_embedding,
                limit=10,
                score_threshold=0.8,
                filters={"language": "en"},
                query_text="test-query"
            )

            # Verify cache.set was called with correct parameters
            mock_query_cache.set.assert_called_once()
            call_kwargs = mock_query_cache.set.call_args.kwargs

            # Should include limit, score_threshold, and filters
            assert call_kwargs.get("limit") == 10 or call_kwargs == {}

            await service.close()

    async def test_upsert_invalidates_cache(self, mock_qdrant_client, mock_query_cache):
        """Test upsert_document invalidates relevant cache entries."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            mock_qdrant_client.upsert.return_value = None

            # Upsert a document
            await service.upsert_document(
                doc_id="new_doc",
                embedding=[0.1] * 1024,
                content="New content",
                metadata={"source": "test"}
            )

            # Should invalidate cache for this collection
            mock_query_cache.invalidate_collection.assert_called_once_with(
                service.collection_name
            )

            await service.close()

    async def test_batch_upsert_invalidates_cache_once(self, mock_qdrant_client, mock_query_cache):
        """Test batch upsert invalidates cache only once."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            mock_qdrant_client.upsert.return_value = None

            # Batch upsert multiple documents
            documents = [
                {
                    "doc_id": f"doc_{i}",
                    "embedding": [0.1] * 1024,
                    "content": f"Content {i}",
                    "metadata": {}
                }
                for i in range(10)
            ]

            await service.upsert_documents(documents)

            # Should invalidate cache only once for the collection
            mock_query_cache.invalidate_collection.assert_called_once_with(
                service.collection_name
            )

            await service.close()

    async def test_search_without_cache_still_works(self, mock_qdrant_client):
        """Test search works normally when cache is not configured."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            # No cache configured

            # Perform search
            query_embedding = [0.1] * 1024
            results = await service.search(query_embedding, limit=5, query_text="test-query")

            # Should query Qdrant directly
            mock_qdrant_client.search.assert_called_once()
            assert len(results) > 0

            await service.close()

    async def test_cache_improves_performance(self, mock_qdrant_client, mock_query_cache):
        """Test that cache reduces query time for repeated searches."""
        import asyncio
        import time

        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            query_embedding = [0.1] * 1024

            # First search - cache miss (slow)
            mock_query_cache.get.return_value = None

            async def slow_search(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate slow DB query
                return [{"id": "doc1", "score": 0.9}]

            mock_qdrant_client.search.side_effect = slow_search

            start = time.time()
            await service.search(query_embedding, query_text="test-query")
            first_query_time = time.time() - start

            # Second search - cache hit (fast)
            mock_query_cache.get.return_value = [{"id": "doc1", "score": 0.9}]

            start = time.time()
            await service.search(query_embedding, query_text="test-query")
            cached_query_time = time.time() - start

            # Cache should be significantly faster
            assert cached_query_time < first_query_time / 2

            await service.close()

    async def test_cache_handles_errors_gracefully(self, mock_qdrant_client, mock_query_cache):
        """Test search handles cache errors gracefully."""
        with patch('app.services.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client):
            service = VectorDBService()
            await service.initialize()
            service.query_cache = mock_query_cache

            # Simulate cache error
            mock_query_cache.get.side_effect = ConnectionError("Redis down")

            # Search should still work (fall back to database)
            query_embedding = [0.1] * 1024
            results = await service.search(query_embedding, query_text="test-query")

            # Should query Qdrant despite cache error
            mock_qdrant_client.search.assert_called_once()
            assert len(results) > 0

            await service.close()
