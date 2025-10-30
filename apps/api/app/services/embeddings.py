"""
TEI (Text Embeddings Inference) service for generating embeddings.
"""

import httpx
from typing import List
from app.core.config import settings


class EmbeddingsService:
    """Service for generating text embeddings using TEI."""

    def __init__(self):
        self.base_url = settings.TEI_URL

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/embed",
                json={"inputs": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
