"""
Tests for scrape endpoint.

Following TDD: Write tests first, watch them fail, then implement.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import TimeoutException, HTTPStatusError, Request, Response

from app.main import app
from app.services.firecrawl import FirecrawlService


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_firecrawl_service():
    """Mock FirecrawlService for dependency injection."""
    service = MagicMock(spec=FirecrawlService)
    service.scrape_url = AsyncMock()
    return service


class TestScrapeRequestValidation:
    """Test suite for ScrapeRequest model validation."""

    def test_valid_formats_accepted(self, client):
        """Test that valid formats are accepted."""
        valid_formats = ["markdown", "html", "rawHtml", "links", "screenshot"]
        
        for fmt in valid_formats:
            # This should succeed (will fail until validation is implemented)
            response = client.post(
                "/api/v1/scrape/",
                json={"url": "https://example.com", "formats": [fmt]},
            )
            # Note: This will 500 because we don't have mock yet, but validation happens first
            assert response.status_code != 422, f"Format {fmt} should be valid"

    def test_invalid_formats_rejected(self, client):
        """Test that invalid formats are rejected with proper error message."""
        # RED: This test should fail because format validation doesn't exist yet
        response = client.post(
            "/api/v1/scrape/",
            json={"url": "https://example.com", "formats": ["invalid_format"]},
        )
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert "Invalid formats" in str(error_detail)
        assert "invalid_format" in str(error_detail)

    def test_multiple_invalid_formats_rejected(self, client):
        """Test that multiple invalid formats are all reported."""
        response = client.post(
            "/api/v1/scrape/",
            json={
                "url": "https://example.com",
                "formats": ["bad1", "markdown", "bad2"],
            },
        )
        
        assert response.status_code == 422
        error_detail = str(response.json()["detail"])
        assert "bad1" in error_detail
        assert "bad2" in error_detail

    def test_default_formats(self, client, mock_firecrawl_service):
        """Test that default formats are markdown and html."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.return_value = {"success": True, "data": {}}

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            response = client.post(
                "/api/v1/scrape/", json={"url": "https://example.com"}
            )

            # Verify the service was called with default formats
            call_args = mock_firecrawl_service.scrape_url.call_args
            assert call_args[0][1]["formats"] == ["markdown", "html"]
        finally:
            app.dependency_overrides.clear()


class TestScrapeDependencyInjection:
    """Test suite for dependency injection pattern."""

    def test_can_override_firecrawl_service(self, client, mock_firecrawl_service):
        """Test that FirecrawlService can be overridden for testing."""
        # RED: This will fail because dependency injection isn't implemented yet
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.return_value = {
            "success": True,
            "data": {"content": "test"},
        }

        # Override the dependency
        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            response = client.post(
                "/api/v1/scrape/",
                json={"url": "https://example.com", "formats": ["markdown"]},
            )

            assert response.status_code == 200
            assert mock_firecrawl_service.scrape_url.called
        finally:
            app.dependency_overrides.clear()

    def test_service_receives_correct_parameters(self, client, mock_firecrawl_service):
        """Test that injected service receives correct parameters."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.return_value = {
            "success": True,
            "data": {},
        }

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            response = client.post(
                "/api/v1/scrape/",
                json={"url": "https://example.com", "formats": ["markdown", "html"]},
            )

            # Verify service was called with correct parameters
            # Note: Pydantic HttpUrl normalizes URLs (adds trailing slash)
            mock_firecrawl_service.scrape_url.assert_called_once_with(
                "https://example.com/", {"formats": ["markdown", "html"]}
            )
        finally:
            app.dependency_overrides.clear()


class TestScrapeExceptionHandling:
    """Test suite for exception handling with proper status codes and logging."""

    def test_timeout_returns_504(self, client, mock_firecrawl_service):
        """Test that timeout exceptions return 504 Gateway Timeout."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        # RED: This will fail because specific exception handling doesn't exist yet
        mock_firecrawl_service.scrape_url.side_effect = TimeoutException("Request timeout")

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            response = client.post(
                "/api/v1/scrape/", json={"url": "https://example.com"}
            )

            assert response.status_code == 504
            assert "timeout" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_http_error_returns_502(self, client, mock_firecrawl_service):
        """Test that HTTP errors from Firecrawl return 502 Bad Gateway."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        request = Request("POST", "https://api.firecrawl.dev/v2/scrape")
        response = Response(500, request=request)
        mock_firecrawl_service.scrape_url.side_effect = HTTPStatusError(
            "Server error", request=request, response=response
        )

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            response = client.post(
                "/api/v1/scrape/", json={"url": "https://example.com"}
            )

            assert response.status_code == 502
            assert "firecrawl" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_unexpected_error_returns_500(self, client, mock_firecrawl_service):
        """Test that unexpected errors return 500 Internal Server Error."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.side_effect = ValueError("Unexpected error")

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            response = client.post(
                "/api/v1/scrape/", json={"url": "https://example.com"}
            )

            assert response.status_code == 500
            assert "internal server error" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @patch("app.api.v1.endpoints.scrape.logger")
    def test_timeout_is_logged(self, mock_logger, client, mock_firecrawl_service):
        """Test that timeout exceptions are logged."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.side_effect = TimeoutException("Timeout")

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            client.post("/api/v1/scrape/", json={"url": "https://example.com"})

            # Verify error was logged
            assert mock_logger.error.called
            log_message = str(mock_logger.error.call_args)
            assert "timeout" in log_message.lower()
        finally:
            app.dependency_overrides.clear()

    @patch("app.api.v1.endpoints.scrape.logger")
    def test_http_error_is_logged(self, mock_logger, client, mock_firecrawl_service):
        """Test that HTTP errors are logged."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        request = Request("POST", "https://api.firecrawl.dev/v2/scrape")
        response = Response(500, request=request)
        mock_firecrawl_service.scrape_url.side_effect = HTTPStatusError(
            "Error", request=request, response=response
        )

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            client.post("/api/v1/scrape/", json={"url": "https://example.com"})

            # Verify error was logged
            assert mock_logger.error.called
        finally:
            app.dependency_overrides.clear()

    @patch("app.api.v1.endpoints.scrape.logger")
    def test_unexpected_error_is_logged_with_exception(
        self, mock_logger, client, mock_firecrawl_service
    ):
        """Test that unexpected errors are logged with full traceback."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.side_effect = RuntimeError("Unexpected")

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            client.post("/api/v1/scrape/", json={"url": "https://example.com"})

            # Verify exception was logged (not just error)
            assert mock_logger.exception.called
        finally:
            app.dependency_overrides.clear()


class TestScrapeOptionsConstruction:
    """Test suite for options construction simplification."""

    def test_formats_always_included_when_provided(self, client, mock_firecrawl_service):
        """Test that formats are always included in options when provided."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.return_value = {"success": True, "data": {}}

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            client.post(
                "/api/v1/scrape/",
                json={"url": "https://example.com", "formats": ["markdown"]},
            )

            # Verify options dict includes formats
            # call_args is (args, kwargs), we want args[1] which is the options dict
            call_args = mock_firecrawl_service.scrape_url.call_args
            assert "formats" in call_args[0][1]
            assert call_args[0][1]["formats"] == ["markdown"]
        finally:
            app.dependency_overrides.clear()

    def test_default_formats_included(self, client, mock_firecrawl_service):
        """Test that default formats are included when not specified."""
        from app.api.v1.endpoints.scrape import get_firecrawl_service

        mock_firecrawl_service.scrape_url.return_value = {"success": True, "data": {}}

        app.dependency_overrides[get_firecrawl_service] = lambda: mock_firecrawl_service

        try:
            client.post("/api/v1/scrape/", json={"url": "https://example.com"})

            # Default formats should be included
            call_args = mock_firecrawl_service.scrape_url.call_args
            assert call_args[0][1]["formats"] == ["markdown", "html"]
        finally:
            app.dependency_overrides.clear()
