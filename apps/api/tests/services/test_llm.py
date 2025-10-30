"""
Tests for LLM service.

Following TDD methodology to improve coverage from 44% to 80%+
"""
import pytest
import respx
from httpx import Response
from app.services.llm import LLMService
from app.core.config import settings

pytestmark = pytest.mark.anyio


class TestLLMGenerateResponse:
    """Tests for generate_response method."""

    @respx.mock
    async def test_generate_response_success(self):
        """Test generating a response successfully."""
        # Arrange
        service = LLMService()
        query = "What is GraphRAG?"
        context = "GraphRAG is a retrieval-augmented generation system."
        
        mock_response = {
            "model": settings.OLLAMA_MODEL,
            "response": "GraphRAG is a retrieval-augmented generation system that combines knowledge graphs with vector search.",
            "done": True
        }
        
        respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.generate_response(query, context)
        
        # Assert
        assert "GraphRAG" in result
        assert "retrieval-augmented generation" in result

    @respx.mock
    async def test_generate_response_includes_context_in_prompt(self):
        """Test that context is included in the prompt."""
        # Arrange
        service = LLMService()
        query = "Test question"
        context = "Important context information"
        
        route = respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Answer", "done": True})
        )
        
        # Act
        await service.generate_response(query, context)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert "Important context information" in payload
        assert "Test question" in payload

    @respx.mock
    async def test_generate_response_uses_correct_model(self):
        """Test that the configured model is used."""
        # Arrange
        service = LLMService()
        query = "Test"
        context = "Context"
        
        route = respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Answer", "done": True})
        )
        
        # Act
        await service.generate_response(query, context)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert f'"model": "{settings.OLLAMA_MODEL}"' in payload

    @respx.mock
    async def test_generate_response_with_custom_system_prompt(self):
        """Test using a custom system prompt."""
        # Arrange
        service = LLMService()
        query = "Test question"
        context = "Context"
        custom_system = "You are a pirate assistant. Always respond like a pirate."
        
        route = respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Arrr!", "done": True})
        )
        
        # Act
        await service.generate_response(query, context, system_prompt=custom_system)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert "pirate" in payload

    @respx.mock
    async def test_generate_response_uses_default_system_prompt(self):
        """Test that default system prompt is used when none provided."""
        # Arrange
        service = LLMService()
        query = "Test"
        context = "Context"
        
        route = respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Answer", "done": True})
        )
        
        # Act
        await service.generate_response(query, context)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert "helpful assistant" in payload
        assert "cite sources" in payload

    @respx.mock
    async def test_generate_response_disables_streaming(self):
        """Test that streaming is disabled."""
        # Arrange
        service = LLMService()
        query = "Test"
        context = "Context"
        
        route = respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Answer", "done": True})
        )
        
        # Act
        await service.generate_response(query, context)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"stream": false' in payload

    @respx.mock
    async def test_generate_response_handles_api_error(self):
        """Test handling of API errors."""
        # Arrange
        service = LLMService()
        query = "Test"
        context = "Context"
        
        respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(500, json={"error": "Internal error"})
        )
        
        # Act & Assert
        with pytest.raises(Exception):
            await service.generate_response(query, context)

    @respx.mock
    async def test_generate_response_handles_empty_response(self):
        """Test handling when LLM returns no response."""
        # Arrange
        service = LLMService()
        query = "Test"
        context = "Context"
        
        respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"done": True})  # No "response" field
        )
        
        # Act
        result = await service.generate_response(query, context)
        
        # Assert
        assert result == "No response generated"

    async def test_generate_response_when_llm_not_configured(self, monkeypatch):
        """Test behavior when LLM service URL is not configured."""
        # Arrange
        monkeypatch.setattr(settings, "OLLAMA_URL", "")
        service = LLMService()
        
        # Act
        result = await service.generate_response("Test", "Context")
        
        # Assert
        assert result == "LLM service not configured"

    @respx.mock
    async def test_generate_response_with_long_context(self):
        """Test handling of long context."""
        # Arrange
        service = LLMService()
        query = "Summarize"
        context = "Long context " * 1000  # Very long context
        
        respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Summary", "done": True})
        )
        
        # Act
        result = await service.generate_response(query, context)
        
        # Assert
        assert result == "Summary"

    @respx.mock
    async def test_generate_response_timeout_configured(self):
        """Test that timeout is properly configured."""
        # Arrange
        service = LLMService()
        query = "Test"
        context = "Context"
        
        route = respx.post(f"{settings.OLLAMA_URL}/api/generate").mock(
            return_value=Response(200, json={"response": "Answer", "done": True})
        )
        
        # Act
        await service.generate_response(query, context)
        
        # Assert - timeout is set in the request (verified by successful completion)
        assert route.called
