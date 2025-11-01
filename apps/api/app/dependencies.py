"""
Dependency injection functions for FastAPI endpoints.
"""

from typing import Optional
from app.services.firecrawl import FirecrawlService

# Global service instances
_firecrawl_service: Optional[FirecrawlService] = None


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
