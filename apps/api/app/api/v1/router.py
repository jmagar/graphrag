"""
API v1 router that combines all endpoint routers.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    crawl,
    scrape,
    query,
    webhooks,
    map,
    search,
    extract,
    conversations,
    chat,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(crawl.router, prefix="/crawl", tags=["crawl"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["scrape"])
api_router.include_router(map.router, prefix="/map", tags=["map"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(extract.router, prefix="/extract", tags=["extract"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
