"""
VectorDB Async Initialization Tests

RED Phase: These tests should FAIL initially (no async methods exist yet)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_db import VectorDBService
from app.core.config import settings


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
