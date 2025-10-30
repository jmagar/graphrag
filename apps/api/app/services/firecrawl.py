"""
Firecrawl v2 API service.
"""
import httpx
from typing import Dict, Any
from app.core.config import settings


class FirecrawlService:
    """Service for interacting with Firecrawl v2 API."""

    def __init__(self):
        self.base_url = settings.FIRECRAWL_URL
        self.api_key = settings.FIRECRAWL_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def start_crawl(self, crawl_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new crawl using Firecrawl v2 API.
        
        POST /v2/crawl
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/crawl",
                json=crawl_options,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_crawl_status(self, crawl_id: str) -> Dict[str, Any]:
        """
        Get the status of a crawl.
        
        GET /v2/crawl/{id}
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/crawl/{crawl_id}",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def cancel_crawl(self, crawl_id: str) -> Dict[str, Any]:
        """
        Cancel a running crawl.
        
        DELETE /v2/crawl/{id}
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/v2/crawl/{crawl_id}",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def scrape_url(self, url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Scrape a single URL.
        
        POST /v2/scrape
        """
        payload = {"url": url}
        if options:
            payload.update(options)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/scrape",
                json=payload,
                headers=self.headers,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()
