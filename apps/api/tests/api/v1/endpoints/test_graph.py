"""Tests for graph endpoints with hybrid search and entity operations."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.api.v1.endpoints.graph import get_hybrid_query_engine, get_graph_db_service

pytestmark = pytest.mark.anyio


class TestGraphSearch:
    """Tests for POST /api/v1/graph/search"""

    async def test_graph_search_success(
        self, test_client: AsyncClient, mock_hybrid_query_engine
    ):
        """Test successful hybrid search."""
        # Mock hybrid search response
        mock_hybrid_query_engine.hybrid_search.return_value = {
            "query": "test query",
            "query_entities": [],
            "vector_results": [
                {"id": "doc1", "score": 0.95, "payload": {"content": "test content"}}
            ],
            "graph_results": [],
            "combined_results": [
                {"id": "doc1", "score": 0.95, "content": "test content", "source": "vector"}
            ],
            "retrieval_strategy": "vector"
        }

        # Override dependency
        app.dependency_overrides[get_hybrid_query_engine] = lambda: mock_hybrid_query_engine

        try:
            payload = {
                "query": "test query",
                "vector_limit": 5,
                "graph_depth": 2,
                "rerank": True
            }

            response = await test_client.post("/api/v1/graph/search", json=payload)
            data = response.json()

            assert response.status_code == 200
            assert "results" in data
            assert "total" in data
            assert "execution_time_ms" in data
            assert data["total"] == 1
            mock_hybrid_query_engine.hybrid_search.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_graph_search_vector_only(
        self, test_client: AsyncClient, mock_hybrid_query_engine
    ):
        """Test search with no entities (vector-only)."""
        mock_hybrid_query_engine.hybrid_search.return_value = {
            "query": "simple query",
            "query_entities": [],
            "vector_results": [{"id": "doc1", "score": 0.9}],
            "graph_results": [],
            "combined_results": [{"id": "doc1", "score": 0.9}],
            "retrieval_strategy": "vector"
        }

        app.dependency_overrides[get_hybrid_query_engine] = lambda: mock_hybrid_query_engine

        try:
            payload = {"query": "simple query"}
            response = await test_client.post("/api/v1/graph/search", json=payload)

            assert response.status_code == 200
            assert response.json()["total"] >= 0
        finally:
            app.dependency_overrides.clear()

    async def test_graph_search_with_reranking_disabled(
        self, test_client: AsyncClient, mock_hybrid_query_engine
    ):
        """Test search with reranking disabled."""
        mock_hybrid_query_engine.hybrid_search.return_value = {
            "query": "test",
            "query_entities": [],
            "vector_results": [],
            "graph_results": [],
            "combined_results": [],
            "retrieval_strategy": "vector"
        }

        app.dependency_overrides[get_hybrid_query_engine] = lambda: mock_hybrid_query_engine

        try:
            payload = {"query": "test", "rerank": False}
            response = await test_client.post("/api/v1/graph/search", json=payload)

            assert response.status_code == 200
            # Verify rerank parameter was passed
            call_args = mock_hybrid_query_engine.hybrid_search.call_args
            assert call_args.kwargs["rerank"] is False
        finally:
            app.dependency_overrides.clear()

    async def test_graph_search_invalid_query(
        self, test_client: AsyncClient, mock_hybrid_query_engine
    ):
        """Test search with invalid/empty query."""
        app.dependency_overrides[get_hybrid_query_engine] = lambda: mock_hybrid_query_engine

        try:
            payload = {"query": ""}

            response = await test_client.post("/api/v1/graph/search", json=payload)

            # FastAPI returns 422 for Pydantic validation errors (min_length=1)
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    async def test_graph_search_empty_results(
        self, test_client: AsyncClient, mock_hybrid_query_engine
    ):
        """Test search with no results found."""
        mock_hybrid_query_engine.hybrid_search.return_value = {
            "query": "no results",
            "query_entities": [],
            "vector_results": [],
            "graph_results": [],
            "combined_results": [],
            "retrieval_strategy": "vector"
        }

        app.dependency_overrides[get_hybrid_query_engine] = lambda: mock_hybrid_query_engine

        try:
            payload = {"query": "no results"}
            response = await test_client.post("/api/v1/graph/search", json=payload)

            assert response.status_code == 200
            assert response.json()["total"] == 0
            assert response.json()["results"] == []
        finally:
            app.dependency_overrides.clear()


class TestEntityConnections:
    """Tests for GET /api/v1/graph/entities/{entity_id}/connections"""

    async def test_get_entity_connections_success(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test successful entity connections retrieval."""
        # Mock entity exists
        mock_graph_db_service.get_entity_by_id.return_value = {
            "id": "test_entity",
            "type": "PERSON",
            "text": "Test Person"
        }
        
        # Mock connections
        mock_graph_db_service.find_connected_entities.return_value = [
            {"id": "entity2", "type": "ORG", "text": "Test Company", "distance": 1},
            {"id": "entity3", "type": "GPE", "text": "Test City", "distance": 1}
        ]

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get("/api/v1/graph/entities/test_entity/connections")
            data = response.json()

            assert response.status_code == 200
            assert data["entity_id"] == "test_entity"
            assert "connections" in data
            assert data["total"] == 2
            assert data["depth"] == 1
        finally:
            app.dependency_overrides.clear()

    async def test_get_entity_connections_not_found(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test entity not found (404)."""
        mock_graph_db_service.get_entity_by_id.return_value = None

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get("/api/v1/graph/entities/nonexistent/connections")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    async def test_get_entity_connections_with_depth(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test connections with depth parameter."""
        mock_graph_db_service.get_entity_by_id.return_value = {"id": "test_entity"}
        mock_graph_db_service.find_connected_entities.return_value = []

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get(
                "/api/v1/graph/entities/test_entity/connections?max_depth=2"
            )

            assert response.status_code == 200
            # Verify depth parameter was passed
            call_args = mock_graph_db_service.find_connected_entities.call_args
            assert call_args.kwargs["max_depth"] == 2
        finally:
            app.dependency_overrides.clear()

    async def test_get_entity_connections_with_relationship_filter(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test connections with relationship type filter."""
        mock_graph_db_service.get_entity_by_id.return_value = {"id": "test_entity"}
        mock_graph_db_service.find_connected_entities.return_value = []

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get(
                "/api/v1/graph/entities/test_entity/connections?relationship_types=WORKS_AT,LOCATED_IN"
            )

            assert response.status_code == 200
            # Verify relationship_types parameter was passed
            call_args = mock_graph_db_service.find_connected_entities.call_args
            assert call_args.kwargs["relationship_types"] == ["WORKS_AT", "LOCATED_IN"]
        finally:
            app.dependency_overrides.clear()


class TestEntitySearch:
    """Tests for GET /api/v1/graph/entities/search"""

    async def test_entity_search_success(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test successful entity search."""
        mock_graph_db_service.search_entities.return_value = [
            {"id": "entity1", "type": "PERSON", "text": "John Doe"},
            {"id": "entity2", "type": "PERSON", "text": "Jane Doe"}
        ]

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get("/api/v1/graph/entities/search?query=Doe")
            data = response.json()

            assert response.status_code == 200
            assert "entities" in data
            assert data["total"] == 2
            assert data["query"] == "Doe"
        finally:
            app.dependency_overrides.clear()

    async def test_entity_search_with_type_filter(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test entity search with entity type filter."""
        mock_graph_db_service.search_entities.return_value = [
            {"id": "entity1", "type": "PERSON", "text": "John Doe"}
        ]

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get(
                "/api/v1/graph/entities/search?query=Doe&entity_types=PERSON,ORG"
            )

            assert response.status_code == 200
            # Verify entity_types parameter was passed
            call_args = mock_graph_db_service.search_entities.call_args
            assert call_args.kwargs["entity_types"] == ["PERSON", "ORG"]
        finally:
            app.dependency_overrides.clear()

    async def test_entity_search_empty_results(
        self, test_client: AsyncClient, mock_graph_db_service
    ):
        """Test entity search with no results."""
        mock_graph_db_service.search_entities.return_value = []

        app.dependency_overrides[get_graph_db_service] = lambda: mock_graph_db_service

        try:
            response = await test_client.get("/api/v1/graph/entities/search?query=nonexistent")
            data = response.json()

            assert response.status_code == 200
            assert data["total"] == 0
            assert data["entities"] == []
        finally:
            app.dependency_overrides.clear()
