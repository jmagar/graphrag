"""
LLM service for generating responses using Ollama.
"""
import httpx
from typing import Optional
from app.core.config import settings


class LLMService:
    """Service for interacting with Ollama LLM."""

    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    async def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a response using the LLM based on the query and context.
        
        Args:
            query: User's question
            context: Retrieved context from vector database
            system_prompt: Optional custom system prompt
            
        Returns:
            Generated response text
        """
        if not self.base_url:
            return "LLM service not configured"

        default_system = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "If the context doesn't contain enough information to answer the question, "
            "say so honestly. Always cite sources when possible."
        )

        prompt = f"""Context:
{context}

Question: {query}

Answer based on the context above:"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or default_system,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response generated")
