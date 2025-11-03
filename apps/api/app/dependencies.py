"""
Dependency injection functions for FastAPI endpoints.
"""

from typing import Optional
from app.services.firecrawl import FirecrawlService
from app.services.vector_db import VectorDBService
from app.services.embeddings import EmbeddingsService
from app.services.llm import LLMService
from app.services.redis_service import RedisService
from app.services.language_detection import LanguageDetectionService
from app.services.graph_db import GraphDBService
from app.services.entity_extractor import EntityExtractor
from app.services.relationship_extractor import RelationshipExtractor

# Global service instances
_firecrawl_service: Optional[FirecrawlService] = None
_vector_db_service: Optional[VectorDBService] = None
_embeddings_service: Optional[EmbeddingsService] = None
_llm_service: Optional[LLMService] = None
_redis_service: Optional[RedisService] = None
_language_detection_service: Optional[LanguageDetectionService] = None
_graph_db_service: Optional[GraphDBService] = None
_entity_extractor: Optional[EntityExtractor] = None
_relationship_extractor: Optional[RelationshipExtractor] = None


def get_firecrawl_service() -> FirecrawlService:
    """
    Get the singleton FirecrawlService instance.
    
    Returns:
        FirecrawlService: Singleton service instance
        
    Raises:
        RuntimeError: If service not initialized (app not started)
    """
    global _firecrawl_service
    if _firecrawl_service is None:
        raise RuntimeError("FirecrawlService not initialized. Application may not be started.")
    return _firecrawl_service


def set_firecrawl_service(service: FirecrawlService) -> None:
    """
    Set the singleton FirecrawlService instance.
    
    Called by the application lifespan manager during startup.
    
    Args:
        service: FirecrawlService instance to use
    """
    global _firecrawl_service
    _firecrawl_service = service


def clear_firecrawl_service() -> None:
    """
    Clear the singleton FirecrawlService instance.
    
    Called by the application lifespan manager during shutdown.
    """
    global _firecrawl_service
    _firecrawl_service = None


# VectorDBService dependency functions
def get_vector_db_service() -> VectorDBService:
    """Get the singleton VectorDBService instance."""
    global _vector_db_service
    if _vector_db_service is None:
        raise RuntimeError("VectorDBService not initialized. Application may not be started.")
    return _vector_db_service


def set_vector_db_service(service: VectorDBService) -> None:
    """Set the singleton VectorDBService instance."""
    global _vector_db_service
    _vector_db_service = service


def clear_vector_db_service() -> None:
    """Clear the singleton VectorDBService instance."""
    global _vector_db_service
    _vector_db_service = None


# EmbeddingsService dependency functions
def get_embeddings_service() -> EmbeddingsService:
    """Get the singleton EmbeddingsService instance."""
    global _embeddings_service
    if _embeddings_service is None:
        raise RuntimeError("EmbeddingsService not initialized. Application may not be started.")
    return _embeddings_service


def set_embeddings_service(service: EmbeddingsService) -> None:
    """Set the singleton EmbeddingsService instance."""
    global _embeddings_service
    _embeddings_service = service


def clear_embeddings_service() -> None:
    """Clear the singleton EmbeddingsService instance."""
    global _embeddings_service
    _embeddings_service = None


# LLMService dependency functions
def get_llm_service() -> LLMService:
    """Get the singleton LLMService instance."""
    global _llm_service
    if _llm_service is None:
        raise RuntimeError("LLMService not initialized. Application may not be started.")
    return _llm_service


def set_llm_service(service: LLMService) -> None:
    """Set the singleton LLMService instance."""
    global _llm_service
    _llm_service = service


def clear_llm_service() -> None:
    """Clear the singleton LLMService instance."""
    global _llm_service
    _llm_service = None


# RedisService dependency functions
def get_redis_service() -> RedisService:
    """Get the singleton RedisService instance."""
    global _redis_service
    if _redis_service is None:
        raise RuntimeError("RedisService not initialized. Application may not be started.")
    return _redis_service


def set_redis_service(service: RedisService) -> None:
    """Set the singleton RedisService instance."""
    global _redis_service
    _redis_service = service


def clear_redis_service() -> None:
    """Clear the singleton RedisService instance."""
    global _redis_service
    _redis_service = None


# LanguageDetectionService dependency functions
def get_language_detection_service() -> LanguageDetectionService:
    """Get the singleton LanguageDetectionService instance."""
    global _language_detection_service
    if _language_detection_service is None:
        raise RuntimeError("LanguageDetectionService not initialized. Application may not be started.")
    return _language_detection_service


def set_language_detection_service(service: LanguageDetectionService) -> None:
    """Set the singleton LanguageDetectionService instance."""
    global _language_detection_service
    _language_detection_service = service


def clear_language_detection_service() -> None:
    """Clear the singleton LanguageDetectionService instance."""
    global _language_detection_service
    _language_detection_service = None


# GraphDBService dependency functions
def get_graph_db_service() -> GraphDBService:
    """Get the singleton GraphDBService instance."""
    global _graph_db_service
    if _graph_db_service is None:
        raise RuntimeError("GraphDBService not initialized. Application may not be started.")
    return _graph_db_service


def set_graph_db_service(service: GraphDBService) -> None:
    """Set the singleton GraphDBService instance."""
    global _graph_db_service
    _graph_db_service = service


def clear_graph_db_service() -> None:
    """Clear the singleton GraphDBService instance."""
    global _graph_db_service
    _graph_db_service = None


# EntityExtractor dependency functions
def get_entity_extractor() -> EntityExtractor:
    """Get the singleton EntityExtractor instance."""
    global _entity_extractor
    if _entity_extractor is None:
        raise RuntimeError("EntityExtractor not initialized. Application may not be started.")
    return _entity_extractor


def set_entity_extractor(service: EntityExtractor) -> None:
    """Set the singleton EntityExtractor instance."""
    global _entity_extractor
    _entity_extractor = service


def clear_entity_extractor() -> None:
    """Clear the singleton EntityExtractor instance."""
    global _entity_extractor
    _entity_extractor = None


# RelationshipExtractor dependency functions
def get_relationship_extractor() -> RelationshipExtractor:
    """Get the singleton RelationshipExtractor instance."""
    global _relationship_extractor
    if _relationship_extractor is None:
        raise RuntimeError("RelationshipExtractor not initialized. Application may not be started.")
    return _relationship_extractor


def set_relationship_extractor(service: RelationshipExtractor) -> None:
    """Set the singleton RelationshipExtractor instance."""
    global _relationship_extractor
    _relationship_extractor = service


def clear_relationship_extractor() -> None:
    """Clear the singleton RelationshipExtractor instance."""
    global _relationship_extractor
    _relationship_extractor = None


# Utility function to clear all services
def clear_all_services() -> None:
    """Clear all singleton service instances."""
    clear_firecrawl_service()
    clear_vector_db_service()
    clear_embeddings_service()
    clear_llm_service()
    clear_redis_service()
    clear_language_detection_service()
    clear_graph_db_service()
    clear_entity_extractor()
    clear_relationship_extractor()
