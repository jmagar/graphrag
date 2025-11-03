"""
Qdrant vector database service.
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Condition,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorDBService:
    """Service for interacting with Qdrant vector database (async)."""

    def __init__(self):
        """
        Initialize the service without blocking operations.

        IMPORTANT: Call initialize() after instantiation to ensure
        collection exists before using the service.
        """
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = settings.QDRANT_COLLECTION

    async def initialize(self) -> None:
        """
        Initialize the async client and ensure collection exists.

        MUST be called after instantiation via lifespan manager.
        Safe to call multiple times (idempotent).
        """
        if self.client is None:
            self.client = AsyncQdrantClient(url=settings.QDRANT_URL)
            logger.info(f"AsyncQdrantClient created for {settings.QDRANT_URL}")

        await self._ensure_collection()
        logger.info(f"✅ VectorDBService initialized with collection: {self.collection_name}")

    async def _ensure_collection(self) -> None:
        """Ensure the collection exists, create if not (async version)."""
        if self.client is None:
            raise RuntimeError("VectorDBService not initialized. Call initialize() first.")

        collections = await self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            # Create collection with appropriate vector size
            # Qwen3-Embedding-0.6B outputs 1024 dimensions
            try:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
                )
            except UnexpectedResponse as exc:
                if exc.status_code != 409:
                    raise
                logger.info(f"Collection {self.collection_name} already created in parallel startup")
            else:
                logger.info(f"Created Qdrant collection: {self.collection_name}")

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("VectorDB client connection closed")

    async def upsert_document(
        self,
        doc_id: str,
        embedding: List[float],
        content: str,
        metadata: Dict[str, Any],
    ):
        """
        Insert or update a document in the vector database.

        Args:
            doc_id: Unique identifier for the document
            embedding: Vector embedding of the content
            content: The text content
            metadata: Additional metadata (url, title, etc.)
        """
        if self.client is None:
            raise RuntimeError("VectorDBService not initialized. Call initialize() first.")

        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={
                "content": content,
                "metadata": metadata,
            },
        )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
            wait=True,
        )

    async def upsert_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Insert or update multiple documents in a single batch operation.

        Optimized for Qdrant batch upserts - much faster than individual upserts.
        For 10 documents: ~50ms vs ~200ms for individual upserts.

        Args:
            documents: List of dicts with keys:
                - doc_id: str (unique identifier)
                - embedding: List[float] (vector embedding)
                - content: str (text content)
                - metadata: dict (additional metadata)
        """
        if not documents:
            return

        if self.client is None:
            raise RuntimeError("VectorDBService not initialized. Call initialize() first.")

        points = [
            PointStruct(
                id=doc["doc_id"],
                vector=doc["embedding"],
                payload={
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                },
            )
            for doc in documents
        ]

        # Single batch upsert to Qdrant
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,  # Wait for write confirmation
        )

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query_embedding: Vector embedding of the query
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score
            filters: Optional filters to apply

        Returns:
            List of matching documents with scores
        """
        if self.client is None:
            raise RuntimeError("VectorDBService not initialized. Call initialize() first.")

        query_filter = None
        if filters:
            conditions: List[Condition] = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                )
            if conditions:
                query_filter = Filter(must=conditions)

        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "content": result.payload.get("content"),
                "metadata": result.payload.get("metadata"),
            }
            for result in results
        ]

    async def delete_document(self, doc_id: str):
        """Delete a document from the vector database."""
        if self.client is None:
            raise RuntimeError("VectorDBService not initialized. Call initialize() first.")

        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=[doc_id],
            wait=True,
        )

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        if self.client is None:
            raise RuntimeError("VectorDBService not initialized. Call initialize() first.")

        info = await self.client.get_collection(collection_name=self.collection_name)
        return {
            "name": self.collection_name,
            "indexed_vectors_count": info.indexed_vectors_count,  # Breaking change: use indexed_vectors_count instead of vectors_count
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "status": info.status.value if hasattr(info.status, "value") else str(info.status),
        }
