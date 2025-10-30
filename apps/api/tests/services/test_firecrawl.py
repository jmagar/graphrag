"""
Tests for Firecrawl service.

Following TDD methodology:
1. RED: Test written first (expecting failure)
2. GREEN: Implementation makes test pass
3. REFACTOR: Improve code while keeping tests green

Priority: HIGH - Service has only 27% coverage
"""
import pytest
import respx
from httpx import Response
from app.services.firecrawl import FirecrawlService
from app.core.config import settings

pytestmark = pytest.mark.anyio


class TestFirecrawlStartCrawl:
    """Tests for start_crawl method."""

    @respx.mock
    async def test_start_crawl_success(self):
        """Test starting a crawl successfully."""
        # Arrange
        service = FirecrawlService()
        crawl_options = {
            "url": "https://example.com",
            "maxDepth": 2,
            "maxPages": 10
        }
        
        mock_response = {
            "id": "crawl_123",
            "status": "started",
            "url": "https://example.com"
        }
        
        # Mock the HTTP request
        respx.post(f"{settings.FIRECRAWL_URL}/v2/crawl").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.start_crawl(crawl_options)
        
        # Assert
        assert result["id"] == "crawl_123"
        assert result["status"] == "started"
        assert result["url"] == "https://example.com"

    @respx.mock
    async def test_start_crawl_sends_correct_headers(self):
        """Test that start_crawl sends authorization header."""
        # Arrange
        service = FirecrawlService()
        crawl_options = {"url": "https://example.com"}
        
        # Mock request
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/crawl").mock(
            return_value=Response(200, json={"id": "crawl_123"})
        )
        
        # Act
        await service.start_crawl(crawl_options)
        
        # Assert
        assert route.called
        request = route.calls.last.request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == f"Bearer {settings.FIRECRAWL_API_KEY}"

    @respx.mock
    async def test_start_crawl_sends_correct_payload(self):
        """Test that start_crawl sends correct JSON payload."""
        # Arrange
        service = FirecrawlService()
        crawl_options = {
            "url": "https://example.com",
            "maxDepth": 3,
            "maxPages": 50
        }
        
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/crawl").mock(
            return_value=Response(200, json={"id": "crawl_123"})
        )
        
        # Act
        await service.start_crawl(crawl_options)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"url": "https://example.com"' in payload
        assert '"maxDepth": 3' in payload
        assert '"maxPages": 50' in payload

    @respx.mock
    async def test_start_crawl_handles_api_error(self):
        """Test that start_crawl raises exception on API error."""
        # Arrange
        service = FirecrawlService()
        crawl_options = {"url": "https://example.com"}
        
        respx.post(f"{settings.FIRECRAWL_URL}/v2/crawl").mock(
            return_value=Response(500, json={"error": "Internal server error"})
        )
        
        # Act & Assert
        with pytest.raises(Exception):
            await service.start_crawl(crawl_options)


class TestFirecrawlGetCrawlStatus:
    """Tests for get_crawl_status method."""

    @respx.mock
    async def test_get_crawl_status_success(self):
        """Test getting crawl status successfully."""
        # Arrange
        service = FirecrawlService()
        crawl_id = "crawl_123"
        
        mock_response = {
            "id": "crawl_123",
            "status": "completed",
            "total": 10,
            "completed": 10,
            "data": []
        }
        
        respx.get(f"{settings.FIRECRAWL_URL}/v2/crawl/{crawl_id}").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.get_crawl_status(crawl_id)
        
        # Assert
        assert result["id"] == "crawl_123"
        assert result["status"] == "completed"
        assert result["total"] == 10
        assert result["completed"] == 10

    @respx.mock
    async def test_get_crawl_status_running(self):
        """Test getting status of running crawl."""
        # Arrange
        service = FirecrawlService()
        crawl_id = "crawl_456"
        
        mock_response = {
            "id": "crawl_456",
            "status": "scraping",
            "total": 20,
            "completed": 5
        }
        
        respx.get(f"{settings.FIRECRAWL_URL}/v2/crawl/{crawl_id}").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.get_crawl_status(crawl_id)
        
        # Assert
        assert result["status"] == "scraping"
        assert result["completed"] < result["total"]

    @respx.mock
    async def test_get_crawl_status_not_found(self):
        """Test getting status of non-existent crawl."""
        # Arrange
        service = FirecrawlService()
        crawl_id = "nonexistent"
        
        respx.get(f"{settings.FIRECRAWL_URL}/v2/crawl/{crawl_id}").mock(
            return_value=Response(404, json={"error": "Crawl not found"})
        )
        
        # Act & Assert
        with pytest.raises(Exception):
            await service.get_crawl_status(crawl_id)


class TestFirecrawlCancelCrawl:
    """Tests for cancel_crawl method."""

    @respx.mock
    async def test_cancel_crawl_success(self):
        """Test canceling a crawl successfully."""
        # Arrange
        service = FirecrawlService()
        crawl_id = "crawl_123"
        
        mock_response = {
            "id": "crawl_123",
            "status": "cancelled"
        }
        
        respx.delete(f"{settings.FIRECRAWL_URL}/v2/crawl/{crawl_id}").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.cancel_crawl(crawl_id)
        
        # Assert
        assert result["id"] == "crawl_123"
        assert result["status"] == "cancelled"

    @respx.mock
    async def test_cancel_crawl_sends_delete_request(self):
        """Test that cancel_crawl sends DELETE request."""
        # Arrange
        service = FirecrawlService()
        crawl_id = "crawl_123"
        
        route = respx.delete(f"{settings.FIRECRAWL_URL}/v2/crawl/{crawl_id}").mock(
            return_value=Response(200, json={"id": "crawl_123", "status": "cancelled"})
        )
        
        # Act
        await service.cancel_crawl(crawl_id)
        
        # Assert
        assert route.called
        assert route.calls.last.request.method == "DELETE"


class TestFirecrawlScrapeUrl:
    """Tests for scrape_url method."""

    @respx.mock
    async def test_scrape_url_success(self):
        """Test scraping a URL successfully."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com/page"
        
        mock_response = {
            "success": True,
            "data": {
                "markdown": "# Example Page\n\nContent here.",
                "metadata": {
                    "sourceURL": url,
                    "title": "Example Page"
                }
            }
        }
        
        respx.post(f"{settings.FIRECRAWL_URL}/v2/scrape").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.scrape_url(url)
        
        # Assert
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["markdown"].startswith("# Example Page")

    @respx.mock
    async def test_scrape_url_with_options(self):
        """Test scraping with additional options."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com/page"
        options = {"onlyMainContent": True}
        
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/scrape").mock(
            return_value=Response(200, json={"success": True, "data": {}})
        )
        
        # Act
        await service.scrape_url(url, options)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"url": "https://example.com/page"' in payload
        assert '"onlyMainContent": true' in payload


class TestFirecrawlMapUrl:
    """Tests for map_url method."""

    @respx.mock
    async def test_map_url_success(self):
        """Test mapping a website successfully."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com"
        
        mock_response = {
            "success": True,
            "data": [
                "https://example.com/page1",
                "https://example.com/page2",
                "https://example.com/page3"
            ]
        }
        
        respx.post(f"{settings.FIRECRAWL_URL}/v2/map").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.map_url(url)
        
        # Assert
        assert result["success"] is True
        assert len(result["data"]) == 3
        assert "https://example.com/page1" in result["data"]

    @respx.mock
    async def test_map_url_with_options(self):
        """Test mapping with search filter."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com"
        options = {"search": "docs"}
        
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/map").mock(
            return_value=Response(200, json={"success": True, "data": []})
        )
        
        # Act
        await service.map_url(url, options)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"search": "docs"' in payload


class TestFirecrawlSearchWeb:
    """Tests for search_web method."""

    @respx.mock
    async def test_search_web_success(self):
        """Test web search successfully."""
        # Arrange
        service = FirecrawlService()
        query = "GraphRAG implementation"
        
        mock_response = {
            "success": True,
            "data": [
                {
                    "url": "https://example.com/result1",
                    "title": "GraphRAG Guide",
                    "markdown": "Content..."
                }
            ]
        }
        
        respx.post(f"{settings.FIRECRAWL_URL}/v2/search").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.search_web(query)
        
        # Assert
        assert result["success"] is True
        assert len(result["data"]) > 0
        assert result["data"][0]["title"] == "GraphRAG Guide"

    @respx.mock
    async def test_search_web_with_limit(self):
        """Test web search with result limit."""
        # Arrange
        service = FirecrawlService()
        query = "test query"
        options = {"limit": 5}
        
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/search").mock(
            return_value=Response(200, json={"success": True, "data": []})
        )
        
        # Act
        await service.search_web(query, options)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"query": "test query"' in payload
        assert '"limit": 5' in payload


class TestFirecrawlExtractData:
    """Tests for extract_data method."""

    @respx.mock
    async def test_extract_data_success(self):
        """Test extracting structured data successfully."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com/product"
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"}
            }
        }
        
        mock_response = {
            "success": True,
            "data": {
                "name": "Product Name",
                "price": 99.99
            }
        }
        
        respx.post(f"{settings.FIRECRAWL_URL}/v2/extract").mock(
            return_value=Response(200, json=mock_response)
        )
        
        # Act
        result = await service.extract_data(url, schema)
        
        # Assert
        assert result["success"] is True
        assert result["data"]["name"] == "Product Name"
        assert result["data"]["price"] == 99.99

    @respx.mock
    async def test_extract_data_sends_schema(self):
        """Test that extract_data sends schema in payload."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com/product"
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/extract").mock(
            return_value=Response(200, json={"success": True, "data": {}})
        )
        
        # Act
        await service.extract_data(url, schema)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"url": "https://example.com/product"' in payload
        assert '"schema":' in payload
        assert '"type": "object"' in payload

    @respx.mock
    async def test_extract_data_with_options(self):
        """Test extracting with additional options."""
        # Arrange
        service = FirecrawlService()
        url = "https://example.com"
        schema = {"type": "object"}
        options = {"timeout": 120}
        
        route = respx.post(f"{settings.FIRECRAWL_URL}/v2/extract").mock(
            return_value=Response(200, json={"success": True, "data": {}})
        )
        
        # Act
        await service.extract_data(url, schema, options)
        
        # Assert
        request = route.calls.last.request
        payload = request.content.decode()
        assert '"timeout": 120' in payload
