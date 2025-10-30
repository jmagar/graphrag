"""
Tests for Vector DB service.

Following TDD methodology to improve coverage from 66% to 80%+
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.vector_db import VectorDBService

pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    with patch("app.services.vector_db.QdrantClient") as mock:
        client = MagicMock()
        mock.return_value = client
        
        # Mock get_collections to return empty list initially
        mock_collections = MagicMock()
        mock_collections.collections = []
        client.get_collections.return_value = mock_collections
        
        yield client


class TestVectorDBInitialization:
    """Tests for VectorDBService initialization."""

    def test_ensure_collection_creates_if_not_exists(self, mock_qdrant_client):
        """Test that collection is created if it doesn't exist."""
        # Arrange
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Act
        service = VectorDBService()
        
        # Assert
        mock_qdrant_client.create_collection.assert_called_once()
        call_args = mock_qdrant_client.create_collection.call_args
        assert call_args.kwargs["collection_name"] == "graphrag"

    def test_ensure_collection_skips_if_exists(self, mock_qdrant_client):
        """Test that collection creation is skipped if it exists."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Act
        service = VectorDBService()
        
        # Assert
        mock_qdrant_client.create_collection.assert_not_called()

    def test_collection_created_with_correct_params(self, mock_qdrant_client):
        """Test that collection is created with correct vector parameters."""
        # Arrange
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Act
        service = VectorDBService()
        
        # Assert
        call_args = mock_qdrant_client.create_collection.call_args
        vectors_config = call_args.kwargs["vectors_config"]
        assert vectors_config.size == 1024
        assert vectors_config.distance.name == "COSINE"


class TestVectorDBUpsertDocument:
    """Tests for upsert_document method."""

    async def test_upsert_document_success(self, mock_qdrant_client):
        """Test upserting a document successfully."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        service = VectorDBService()
        
        doc_id = "doc123"
        embedding = [0.1] * 1024
        content = "Test content"
        metadata = {"url": "https://example.com", "title": "Test"}
        
        # Act
        await service.upsert_document(doc_id, embedding, content, metadata)
        
        # Assert
        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "graphrag"
        assert call_args.kwargs["wait"] is True

    async def test_upsert_document_creates_point_with_correct_structure(self, mock_qdrant_client):
        """Test that PointStruct is created with correct data."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        service = VectorDBService()
        
        doc_id = "doc456"
        embedding = [0.2] * 1024
        content = "Another test"
        metadata = {"url": "https://test.com"}
        
        # Act
        await service.upsert_document(doc_id, embedding, content, metadata)
        
        # Assert
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points) == 1
        point = points[0]
        assert point.id == doc_id
        assert point.vector == embedding
        assert point.payload["content"] == content
        assert point.payload["metadata"] == metadata


class TestVectorDBSearch:
    """Tests for search method."""

    async def test_search_returns_results(self, mock_qdrant_client):
        """Test searching returns formatted results."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "doc1"
        mock_result.score = 0.95
        mock_result.payload = {
            "content": "Test content",
            "metadata": {"url": "https://example.com"}
        }
        mock_qdrant_client.search.return_value = [mock_result]
        
        service = VectorDBService()
        query_embedding = [0.1] * 1024
        
        # Act
        results = await service.search(query_embedding, limit=5)
        
        # Assert
        assert len(results) == 1
        assert results[0]["id"] == "doc1"
        assert results[0]["score"] == 0.95
        assert results[0]["content"] == "Test content"
        assert results[0]["metadata"]["url"] == "https://example.com"

    async def test_search_with_score_threshold(self, mock_qdrant_client):
        """Test search with score threshold."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        mock_qdrant_client.search.return_value = []
        
        service = VectorDBService()
        query_embedding = [0.1] * 1024
        
        # Act
        await service.search(query_embedding, limit=10, score_threshold=0.8)
        
        # Assert
        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs["score_threshold"] == 0.8

    async def test_search_with_filters(self, mock_qdrant_client):
        """Test search with metadata filters."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        mock_qdrant_client.search.return_value = []
        
        service = VectorDBService()
        query_embedding = [0.1] * 1024
        filters = {"domain": "example.com"}
        
        # Act
        await service.search(query_embedding, filters=filters)
        
        # Assert
        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs["query_filter"] is not None

    async def test_search_without_filters(self, mock_qdrant_client):
        """Test search without filters."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        mock_qdrant_client.search.return_value = []
        
        service = VectorDBService()
        query_embedding = [0.1] * 1024
        
        # Act
        await service.search(query_embedding)
        
        # Assert
        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs["query_filter"] is None

    async def test_search_with_custom_limit(self, mock_qdrant_client):
        """Test search with custom result limit."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        mock_qdrant_client.search.return_value = []
        
        service = VectorDBService()
        query_embedding = [0.1] * 1024
        
        # Act
        await service.search(query_embedding, limit=20)
        
        # Assert
        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs["limit"] == 20


class TestVectorDBDeleteDocument:
    """Tests for delete_document method."""

    async def test_delete_document_success(self, mock_qdrant_client):
        """Test deleting a document successfully."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        service = VectorDBService()
        doc_id = "doc_to_delete"
        
        # Act
        await service.delete_document(doc_id)
        
        # Assert
        mock_qdrant_client.delete.assert_called_once()
        call_args = mock_qdrant_client.delete.call_args
        assert call_args.kwargs["collection_name"] == "graphrag"
        assert doc_id in call_args.kwargs["points_selector"]
        assert call_args.kwargs["wait"] is True


class TestVectorDBGetCollectionInfo:
    """Tests for get_collection_info method."""

    async def test_get_collection_info_returns_stats(self, mock_qdrant_client):
        """Test getting collection information."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        # Mock collection info
        mock_info = MagicMock()
        mock_info.vectors_count = 100
        mock_info.points_count = 50
        mock_info.status = "green"
        mock_qdrant_client.get_collection.return_value = mock_info
        
        service = VectorDBService()
        
        # Act
        info = await service.get_collection_info()
        
        # Assert
        assert info["name"] == "graphrag"
        assert info["vectors_count"] == 100
        assert info["points_count"] == 50
        assert info["status"] == "green"

    async def test_get_collection_info_calls_correct_collection(self, mock_qdrant_client):
        """Test that get_collection_info queries the correct collection."""
        # Arrange
        mock_collection = MagicMock()
        mock_collection.name = "graphrag"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        mock_info = MagicMock()
        mock_info.vectors_count = 0
        mock_info.points_count = 0
        mock_info.status = "green"
        mock_qdrant_client.get_collection.return_value = mock_info
        
        service = VectorDBService()
        
        # Act
        await service.get_collection_info()
        
        # Assert
        mock_qdrant_client.get_collection.assert_called_once_with(
            collection_name="graphrag"
        )
