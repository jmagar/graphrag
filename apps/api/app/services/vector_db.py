"""
Qdrant vector database service.
"""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings


class VectorDBService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists, create if not."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            # Create collection with appropriate vector size
            # Adjust size based on your embedding model (e.g., 768 for many models)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

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
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={
                "content": content,
                "metadata": metadata,
            },
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
            wait=True,
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
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                )
            if conditions:
                query_filter = Filter(must=conditions)

        results = self.client.search(
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
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[doc_id],
            wait=True,
        )

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        info = self.client.get_collection(collection_name=self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
        }
