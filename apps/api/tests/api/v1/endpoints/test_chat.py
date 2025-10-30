"""Tests for chat endpoint with RAG integration."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID

pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_llm_service():
    """Mock LLM service that returns a simple response."""
    with patch("app.api.v1.endpoints.chat.LLMService") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.generate_response.return_value = "This is a test response from the LLM."
        mock_cls.return_value = mock_instance
        yield mock_instance


class TestChatWithRAG:
    """Tests for POST /api/v1/chat"""

    async def test_chat_creates_new_conversation_if_none_provided(
        self, test_client: AsyncClient, mock_llm_service
    ):
        """Test chat creates a new conversation when conversation_id is not provided."""
        payload = {
            "message": "Hello, world!",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        
        assert response.status_code == 200
        assert "conversation_id" in data
        assert UUID(data["conversation_id"])

    async def test_chat_uses_existing_conversation(
        self, test_client: AsyncClient, mock_llm_service
    ):
        """Test chat uses existing conversation when conversation_id provided."""
        # Create conversation
        conv_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test Chat"}
        )
        conv_id = conv_response.json()["id"]
        
        # Send chat message
        payload = {
            "conversation_id": conv_id,
            "message": "Hello!",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        
        assert response.status_code == 200
        assert data["conversation_id"] == conv_id

    async def test_chat_saves_user_message(self, test_client: AsyncClient):
        """Test chat saves user message to conversation."""
        payload = {
            "message": "What is GraphRAG?",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        conv_id = data["conversation_id"]
        
        # Check conversation has user message
        conv_response = await test_client.get(f"/api/v1/conversations/{conv_id}")
        conv_data = conv_response.json()
        
        assert len(conv_data["messages"]) >= 1
        assert any(m["role"] == "user" and m["content"] == "What is GraphRAG?" 
                   for m in conv_data["messages"])

    async def test_chat_saves_assistant_message(self, test_client: AsyncClient):
        """Test chat saves assistant response to conversation."""
        payload = {
            "message": "Hello!",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        conv_id = data["conversation_id"]
        
        # Check conversation has assistant message
        conv_response = await test_client.get(f"/api/v1/conversations/{conv_id}")
        conv_data = conv_response.json()
        
        assert len(conv_data["messages"]) >= 2  # User + Assistant
        assert any(m["role"] == "assistant" for m in conv_data["messages"])

    async def test_chat_returns_message_response(self, test_client: AsyncClient):
        """Test chat returns the assistant message in response."""
        payload = {
            "message": "Hello!",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert "content" in data["message"]
        assert len(data["message"]["content"]) > 0

    @patch("app.api.v1.endpoints.chat.VectorDBService")
    @patch("app.api.v1.endpoints.chat.EmbeddingsService")
    async def test_chat_with_rag_enabled_queries_vector_db(
        self, mock_embeddings_cls, mock_vector_db_cls, test_client: AsyncClient
    ):
        """Test chat with RAG enabled queries vector database."""
        # Setup mocks
        mock_embeddings = AsyncMock()
        mock_embeddings.generate_embedding.return_value = [0.1] * 768
        mock_embeddings_cls.return_value = mock_embeddings
        
        mock_vector_db = AsyncMock()
        mock_vector_db.search.return_value = [
            {
                "id": "doc1",
                "score": 0.95,
                "payload": {
                    "content": "GraphRAG is a RAG system",
                    "metadata": {"sourceURL": "https://example.com"}
                }
            }
        ]
        mock_vector_db_cls.return_value = mock_vector_db
        
        payload = {
            "message": "What is GraphRAG?",
            "use_rag": True,
            "limit": 5
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        
        assert response.status_code == 200
        # Verify embeddings were generated
        mock_embeddings.generate_embedding.assert_called_once_with("What is GraphRAG?")
        # Verify vector search was performed
        mock_vector_db.search.assert_called_once()

    @patch("app.api.v1.endpoints.chat.VectorDBService")
    @patch("app.api.v1.endpoints.chat.EmbeddingsService")
    async def test_chat_returns_sources_when_rag_enabled(
        self, mock_embeddings_cls, mock_vector_db_cls, test_client: AsyncClient
    ):
        """Test chat returns RAG sources when enabled."""
        # Setup mocks
        mock_embeddings = AsyncMock()
        mock_embeddings.generate_embedding.return_value = [0.1] * 768
        mock_embeddings_cls.return_value = mock_embeddings
        
        mock_vector_db = AsyncMock()
        mock_vector_db.search.return_value = [
            {
                "id": "doc1",
                "score": 0.95,
                "payload": {
                    "content": "GraphRAG content",
                    "metadata": {"sourceURL": "https://example.com"}
                }
            }
        ]
        mock_vector_db_cls.return_value = mock_vector_db
        
        payload = {
            "message": "Tell me about GraphRAG",
            "use_rag": True
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        
        assert "sources" in data
        assert len(data["sources"]) > 0

    async def test_chat_without_rag_has_empty_sources(self, test_client: AsyncClient):
        """Test chat without RAG returns empty sources."""
        payload = {
            "message": "Hello!",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        
        assert "sources" in data
        assert data["sources"] == []

    @patch("app.api.v1.endpoints.chat.LLMService")
    @patch("app.api.v1.endpoints.chat.VectorDBService")
    @patch("app.api.v1.endpoints.chat.EmbeddingsService")
    async def test_chat_passes_context_to_llm(
        self, mock_embeddings_cls, mock_vector_db_cls, mock_llm_cls, test_client: AsyncClient
    ):
        """Test chat passes vector search results as context to LLM."""
        # Setup mocks
        mock_embeddings = AsyncMock()
        mock_embeddings.generate_embedding.return_value = [0.1] * 768
        mock_embeddings_cls.return_value = mock_embeddings
        
        mock_vector_db = AsyncMock()
        mock_vector_db.search.return_value = [
            {
                "id": "doc1",
                "score": 0.95,
                "payload": {
                    "content": "Context content",
                    "metadata": {"sourceURL": "https://example.com"}
                }
            }
        ]
        mock_vector_db_cls.return_value = mock_vector_db
        
        mock_llm = AsyncMock()
        mock_llm.generate_response.return_value = "LLM response"
        mock_llm_cls.return_value = mock_llm
        
        payload = {
            "message": "Question?",
            "use_rag": True
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        
        assert response.status_code == 200
        # Verify LLM was called with context
        mock_llm.generate_response.assert_called_once()
        call_args = mock_llm.generate_response.call_args
        assert "query" in call_args.kwargs
        assert "context" in call_args.kwargs
        assert len(call_args.kwargs["context"]) > 0

    async def test_chat_generates_conversation_title_from_first_message(
        self, test_client: AsyncClient
    ):
        """Test chat generates conversation title from first user message."""
        payload = {
            "message": "What is machine learning?",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        data = response.json()
        conv_id = data["conversation_id"]
        
        # Get conversation
        conv_response = await test_client.get(f"/api/v1/conversations/{conv_id}")
        conv_data = conv_response.json()
        
        # Title should be based on first message
        assert conv_data["title"] != ""
        assert len(conv_data["title"]) > 0

    async def test_chat_handles_invalid_conversation_id(self, test_client: AsyncClient):
        """Test chat handles non-existent conversation ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        payload = {
            "conversation_id": fake_id,
            "message": "Hello!",
            "use_rag": False
        }
        
        response = await test_client.post("/api/v1/chat/", json=payload)
        
        assert response.status_code == 404
