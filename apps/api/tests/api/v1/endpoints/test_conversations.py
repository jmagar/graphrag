"""Tests for conversation API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import UUID

pytestmark = pytest.mark.anyio


class TestCreateConversation:
    """Tests for POST /api/v1/conversations/"""

    async def test_create_conversation_returns_201(self, test_client: AsyncClient):
        """Test creating a conversation returns 201 status."""
        payload = {"title": "Test Conversation"}
        
        response = await test_client.post("/api/v1/conversations/", json=payload)
        
        assert response.status_code == 201

    async def test_create_conversation_returns_valid_structure(self, test_client: AsyncClient):
        """Test created conversation has correct structure."""
        payload = {"title": "Test Conversation", "space": "work"}
        
        response = await test_client.post("/api/v1/conversations/", json=payload)
        data = response.json()
        
        assert "id" in data
        assert UUID(data["id"])  # Valid UUID
        assert data["title"] == "Test Conversation"
        assert data["space"] == "work"
        assert "created_at" in data
        assert "updated_at" in data
        assert data["tags"] == []
        assert data["message_count"] == 0

    async def test_create_conversation_with_default_space(self, test_client: AsyncClient):
        """Test conversation defaults to 'default' space."""
        payload = {"title": "Test"}
        
        response = await test_client.post("/api/v1/conversations/", json=payload)
        data = response.json()
        
        assert data["space"] == "default"

    async def test_create_conversation_with_initial_message(self, test_client: AsyncClient):
        """Test creating conversation with initial message."""
        payload = {
            "title": "Test Conversation",
            "initial_message": {
                "role": "user",
                "content": "Hello, world!"
            }
        }
        
        response = await test_client.post("/api/v1/conversations/", json=payload)
        data = response.json()
        
        assert response.status_code == 201
        assert data["message_count"] == 1
        assert data["last_message_preview"] == "Hello, world!"

    async def test_create_conversation_requires_title(self, test_client: AsyncClient):
        """Test that title is required."""
        payload = {"space": "work"}
        
        response = await test_client.post("/api/v1/conversations/", json=payload)
        
        assert response.status_code == 422


class TestListConversations:
    """Tests for GET /api/v1/conversations/"""

    async def test_list_conversations_returns_200(self, test_client: AsyncClient):
        """Test listing conversations returns 200."""
        response = await test_client.get("/api/v1/conversations/")
        
        assert response.status_code == 200

    async def test_list_conversations_returns_array(self, test_client: AsyncClient):
        """Test listing returns an array."""
        response = await test_client.get("/api/v1/conversations/")
        data = response.json()
        
        assert isinstance(data, list)

    async def test_list_conversations_returns_created_conversation(self, test_client: AsyncClient):
        """Test list includes created conversations."""
        # Create a conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test Conversation"}
        )
        created_id = create_response.json()["id"]
        
        # List conversations
        list_response = await test_client.get("/api/v1/conversations/")
        data = list_response.json()
        
        assert len(data) > 0
        assert any(c["id"] == created_id for c in data)

    async def test_list_conversations_filters_by_space(self, test_client: AsyncClient):
        """Test filtering conversations by space."""
        # Create conversations in different spaces
        await test_client.post("/api/v1/conversations/", json={"title": "Work 1", "space": "work"})
        await test_client.post("/api/v1/conversations/", json={"title": "Personal 1", "space": "personal"})
        
        # Filter by work space
        response = await test_client.get("/api/v1/conversations/?space=work")
        data = response.json()
        
        assert all(c["space"] == "work" for c in data)

    async def test_list_conversations_with_limit(self, test_client: AsyncClient):
        """Test limiting number of results."""
        # Create multiple conversations
        for i in range(5):
            await test_client.post("/api/v1/conversations/", json={"title": f"Conv {i}"})
        
        # Get with limit
        response = await test_client.get("/api/v1/conversations/?limit=3")
        data = response.json()
        
        assert len(data) <= 3


class TestGetConversation:
    """Tests for GET /api/v1/conversations/{id}"""

    async def test_get_conversation_returns_200(self, test_client: AsyncClient):
        """Test getting a conversation returns 200."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Get conversation
        response = await test_client.get(f"/api/v1/conversations/{conv_id}")
        
        assert response.status_code == 200

    async def test_get_conversation_includes_messages(self, test_client: AsyncClient):
        """Test getting conversation includes messages."""
        # Create conversation with initial message
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={
                "title": "Test",
                "initial_message": {"role": "user", "content": "Hello"}
            }
        )
        conv_id = create_response.json()["id"]
        
        # Get conversation
        response = await test_client.get(f"/api/v1/conversations/{conv_id}")
        data = response.json()
        
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello"

    async def test_get_conversation_not_found(self, test_client: AsyncClient):
        """Test getting non-existent conversation returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = await test_client.get(f"/api/v1/conversations/{fake_id}")
        
        assert response.status_code == 404


class TestUpdateConversation:
    """Tests for PUT /api/v1/conversations/{id}"""

    async def test_update_conversation_title(self, test_client: AsyncClient):
        """Test updating conversation title."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Old Title"}
        )
        conv_id = create_response.json()["id"]
        
        # Update title
        update_response = await test_client.put(
            f"/api/v1/conversations/{conv_id}",
            json={"title": "New Title"}
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "New Title"

    async def test_update_conversation_tags(self, test_client: AsyncClient):
        """Test updating conversation tags."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Update tags
        update_response = await test_client.put(
            f"/api/v1/conversations/{conv_id}",
            json={"tags": ["work", "urgent"]}
        )
        data = update_response.json()
        
        assert update_response.status_code == 200
        assert set(data["tags"]) == {"work", "urgent"}


class TestDeleteConversation:
    """Tests for DELETE /api/v1/conversations/{id}"""

    async def test_delete_conversation_returns_204(self, test_client: AsyncClient):
        """Test deleting conversation returns 204."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Delete conversation
        response = await test_client.delete(f"/api/v1/conversations/{conv_id}")
        
        assert response.status_code == 204

    async def test_delete_conversation_removes_it(self, test_client: AsyncClient):
        """Test deleted conversation is no longer accessible."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Delete conversation
        await test_client.delete(f"/api/v1/conversations/{conv_id}")
        
        # Try to get it
        get_response = await test_client.get(f"/api/v1/conversations/{conv_id}")
        
        assert get_response.status_code == 404


class TestAddMessage:
    """Tests for POST /api/v1/conversations/{id}/messages"""

    async def test_add_message_returns_201(self, test_client: AsyncClient):
        """Test adding message returns 201."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Add message
        response = await test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"role": "user", "content": "Hello!"}
        )
        
        assert response.status_code == 201

    async def test_add_message_returns_message_data(self, test_client: AsyncClient):
        """Test adding message returns message data."""
        # Create conversation
        create_response = await test_client.post(
            "/api/v1/conversations/",
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Add message
        response = await test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"role": "user", "content": "Hello!"}
        )
        data = response.json()
        
        assert "id" in data
        assert data["conversation_id"] == conv_id
        assert data["role"] == "user"
        assert data["content"] == "Hello!"
        assert "created_at" in data
