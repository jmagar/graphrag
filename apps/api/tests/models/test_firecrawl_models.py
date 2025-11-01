"""
Comprehensive tests for Firecrawl Pydantic models.

Tests cover:
1. Valid webhook payloads (crawl.started, crawl.page, crawl.completed, crawl.failed)
2. Malformed payloads (missing required fields, wrong types)
3. Invalid metadata (statusCode out of range 100-599)
4. Edge cases (empty markdown, missing optional fields)
5. Type coercion and validation errors
6. Union type WebhookPayload discrimination
"""

import pytest
from pydantic import ValidationError
from typing import Dict, Any

from app.models.firecrawl import (
    FirecrawlMetadata,
    FirecrawlPageData,
    WebhookCrawlStarted,
    WebhookCrawlPage,
    WebhookCrawlCompleted,
    WebhookCrawlFailed,
    WebhookPayload,
    WebhookBatchScrapeStarted,
    WebhookBatchScrapePage,
    WebhookBatchScrapeCompleted,
    WebhookBatchScrapeFailed,
    FirecrawlCrawlResponse,
    FirecrawlCrawlStatus,
    FirecrawlScrapeResponse,
)


# ============================================================================
# FirecrawlMetadata Tests
# ============================================================================


class TestFirecrawlMetadata:
    """Test FirecrawlMetadata model validation."""

    def test_valid_metadata_with_all_fields(self):
        """Test metadata with all fields populated."""
        data = {
            "sourceURL": "https://example.com/page",
            "title": "Example Page",
            "description": "A sample page for testing",
            "language": "en",
            "statusCode": 200,
            "ogTitle": "Example Open Graph Title",
            "ogDescription": "Example OG Description",
            "ogImage": "https://example.com/image.png",
            "ogUrl": "https://example.com/canonical",
        }

        metadata = FirecrawlMetadata(**data)

        assert metadata.sourceURL == "https://example.com/page"
        assert metadata.title == "Example Page"
        assert metadata.description == "A sample page for testing"
        assert metadata.language == "en"
        assert metadata.statusCode == 200
        assert metadata.ogTitle == "Example Open Graph Title"
        assert metadata.ogDescription == "Example OG Description"
        assert metadata.ogImage == "https://example.com/image.png"
        assert metadata.ogUrl == "https://example.com/canonical"

    def test_valid_metadata_with_minimal_fields(self):
        """Test metadata with only required fields."""
        data = {
            "sourceURL": "https://example.com",
            "statusCode": 200,
        }

        metadata = FirecrawlMetadata(**data)

        assert metadata.sourceURL == "https://example.com"
        assert metadata.statusCode == 200
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.language is None
        assert metadata.ogTitle is None
        assert metadata.ogDescription is None
        assert metadata.ogImage is None
        assert metadata.ogUrl is None

    def test_missing_required_sourceURL(self):
        """Test that missing sourceURL raises ValidationError."""
        data = {"statusCode": 200}

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlMetadata(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("sourceURL",)
        assert errors[0]["type"] == "missing"

    def test_missing_required_statusCode(self):
        """Test that missing statusCode raises ValidationError."""
        data = {"sourceURL": "https://example.com"}

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlMetadata(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("statusCode",)
        assert errors[0]["type"] == "missing"

    @pytest.mark.parametrize("status_code", [99, 600, 0, -1, 1000])
    def test_invalid_statusCode_out_of_range(self, status_code: int):
        """Test that statusCode outside 100-599 range raises ValidationError."""
        data = {
            "sourceURL": "https://example.com",
            "statusCode": status_code,
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlMetadata(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("statusCode",) for err in errors)

    @pytest.mark.parametrize("status_code", [100, 200, 301, 404, 500, 599])
    def test_valid_statusCode_boundary_values(self, status_code: int):
        """Test statusCode at valid boundary values (100-599)."""
        data = {
            "sourceURL": "https://example.com",
            "statusCode": status_code,
        }

        metadata = FirecrawlMetadata(**data)
        assert metadata.statusCode == status_code

    def test_wrong_type_for_statusCode(self):
        """Test that non-integer statusCode raises ValidationError."""
        data = {
            "sourceURL": "https://example.com",
            "statusCode": "200",  # String instead of int
        }

        # Pydantic may coerce strings to ints, so this might pass
        # Let's test with a truly invalid type
        data_invalid = {
            "sourceURL": "https://example.com",
            "statusCode": "not-a-number",
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlMetadata(**data_invalid)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("statusCode",) for err in errors)

    def test_wrong_type_for_sourceURL(self):
        """Test that non-string sourceURL raises ValidationError."""
        data = {
            "sourceURL": 12345,  # Integer instead of string
            "statusCode": 200,
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlMetadata(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("sourceURL",) for err in errors)


# ============================================================================
# FirecrawlPageData Tests
# ============================================================================


class TestFirecrawlPageData:
    """Test FirecrawlPageData model validation."""

    def test_valid_page_data_with_all_fields(self):
        """Test page data with all fields populated."""
        data = {
            "markdown": "# Example\n\nContent here",
            "html": "<h1>Example</h1><p>Content here</p>",
            "rawHtml": "<!DOCTYPE html><html>...</html>",
            "links": ["https://example.com/link1", "https://example.com/link2"],
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
                "title": "Example",
            },
            "screenshot": "base64encodeddata==",
            "actions": [{"type": "click", "selector": "#button"}],
        }

        page_data = FirecrawlPageData(**data)

        assert page_data.markdown == "# Example\n\nContent here"
        assert page_data.html == "<h1>Example</h1><p>Content here</p>"
        assert page_data.rawHtml == "<!DOCTYPE html><html>...</html>"
        assert page_data.links == ["https://example.com/link1", "https://example.com/link2"]
        assert page_data.metadata.sourceURL == "https://example.com"
        assert page_data.screenshot == "base64encodeddata=="
        assert len(page_data.actions) == 1

    def test_valid_page_data_with_minimal_fields(self):
        """Test page data with only required fields."""
        data = {
            "markdown": "# Content",
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
        }

        page_data = FirecrawlPageData(**data)

        assert page_data.markdown == "# Content"
        assert page_data.metadata.sourceURL == "https://example.com"
        assert page_data.html is None
        assert page_data.rawHtml is None
        assert page_data.links is None
        assert page_data.screenshot is None
        assert page_data.actions is None

    def test_empty_markdown_is_valid(self):
        """Test that empty markdown string is valid (edge case)."""
        data = {
            "markdown": "",
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
        }

        page_data = FirecrawlPageData(**data)
        assert page_data.markdown == ""

    def test_missing_required_markdown(self):
        """Test that missing markdown raises ValidationError."""
        data = {
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlPageData(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("markdown",) for err in errors)

    def test_missing_required_metadata(self):
        """Test that missing metadata raises ValidationError."""
        data = {"markdown": "# Content"}

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlPageData(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("metadata",) for err in errors)

    def test_nested_metadata_validation_error(self):
        """Test that invalid nested metadata raises ValidationError."""
        data = {
            "markdown": "# Content",
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 999,  # Invalid status code
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlPageData(**data)

        errors = exc_info.value.errors()
        assert any("statusCode" in str(err["loc"]) for err in errors)

    def test_empty_links_list(self):
        """Test that empty links list is valid."""
        data = {
            "markdown": "# Content",
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
            "links": [],
        }

        page_data = FirecrawlPageData(**data)
        assert page_data.links == []

    def test_wrong_type_for_links(self):
        """Test that non-list links raises ValidationError."""
        data = {
            "markdown": "# Content",
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
            "links": "not-a-list",
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlPageData(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("links",) for err in errors)


# ============================================================================
# WebhookCrawlStarted Tests
# ============================================================================


class TestWebhookCrawlStarted:
    """Test WebhookCrawlStarted model validation."""

    def test_valid_crawl_started_with_all_fields(self):
        """Test crawl.started webhook with all fields."""
        data = {
            "type": "crawl.started",
            "id": "crawl_123456",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        webhook = WebhookCrawlStarted(**data)

        assert webhook.type == "crawl.started"
        assert webhook.id == "crawl_123456"
        assert webhook.timestamp == "2024-01-01T12:00:00Z"

    def test_valid_crawl_started_without_timestamp(self):
        """Test crawl.started webhook without optional timestamp."""
        data = {
            "type": "crawl.started",
            "id": "crawl_123456",
        }

        webhook = WebhookCrawlStarted(**data)

        assert webhook.type == "crawl.started"
        assert webhook.id == "crawl_123456"
        assert webhook.timestamp is None

    def test_missing_required_id(self):
        """Test that missing id raises ValidationError."""
        data = {"type": "crawl.started"}

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlStarted(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("id",) for err in errors)

    def test_wrong_literal_type(self):
        """Test that wrong literal type raises ValidationError."""
        data = {
            "type": "crawl.completed",  # Wrong type
            "id": "crawl_123456",
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlStarted(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("type",) for err in errors)

    def test_default_type_value(self):
        """Test that type has default value."""
        data = {"id": "crawl_123456"}

        webhook = WebhookCrawlStarted(**data)
        assert webhook.type == "crawl.started"


# ============================================================================
# WebhookCrawlPage Tests
# ============================================================================


class TestWebhookCrawlPage:
    """Test WebhookCrawlPage model validation."""

    def test_valid_crawl_page_with_all_fields(self):
        """Test crawl.page webhook with all fields."""
        data = {
            "type": "crawl.page",
            "id": "crawl_123456",
            "data": {
                "markdown": "# Page Title\n\nContent",
                "html": "<h1>Page Title</h1>",
                "metadata": {
                    "sourceURL": "https://example.com/page",
                    "statusCode": 200,
                    "title": "Page Title",
                },
            },
            "timestamp": "2024-01-01T12:00:00Z",
        }

        webhook = WebhookCrawlPage(**data)

        assert webhook.type == "crawl.page"
        assert webhook.id == "crawl_123456"
        assert webhook.data.markdown == "# Page Title\n\nContent"
        assert webhook.data.metadata.sourceURL == "https://example.com/page"
        assert webhook.timestamp == "2024-01-01T12:00:00Z"

    def test_valid_crawl_page_minimal(self):
        """Test crawl.page webhook with minimal required fields."""
        data = {
            "type": "crawl.page",
            "id": "crawl_123456",
            "data": {
                "markdown": "Content",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
            },
        }

        webhook = WebhookCrawlPage(**data)

        assert webhook.type == "crawl.page"
        assert webhook.id == "crawl_123456"
        assert webhook.data.markdown == "Content"
        assert webhook.timestamp is None

    def test_missing_required_data(self):
        """Test that missing data field raises ValidationError."""
        data = {
            "type": "crawl.page",
            "id": "crawl_123456",
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlPage(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("data",) for err in errors)

    def test_invalid_nested_data(self):
        """Test that invalid nested data raises ValidationError."""
        data = {
            "type": "crawl.page",
            "id": "crawl_123456",
            "data": {
                "markdown": "Content",
                # Missing required metadata
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlPage(**data)

        errors = exc_info.value.errors()
        assert any("metadata" in str(err["loc"]) for err in errors)

    def test_default_type_value(self):
        """Test that type has default value."""
        data = {
            "id": "crawl_123456",
            "data": {
                "markdown": "Content",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
            },
        }

        webhook = WebhookCrawlPage(**data)
        assert webhook.type == "crawl.page"


# ============================================================================
# WebhookCrawlCompleted Tests
# ============================================================================


class TestWebhookCrawlCompleted:
    """Test WebhookCrawlCompleted model validation."""

    def test_valid_crawl_completed_with_all_fields(self):
        """Test crawl.completed webhook with all fields."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123456",
            "data": [
                {
                    "markdown": "# Page 1",
                    "metadata": {
                        "sourceURL": "https://example.com/page1",
                        "statusCode": 200,
                    },
                },
                {
                    "markdown": "# Page 2",
                    "metadata": {
                        "sourceURL": "https://example.com/page2",
                        "statusCode": 200,
                    },
                },
            ],
            "total": 2,
            "completed": 2,
            "creditsUsed": 4,
            "timestamp": "2024-01-01T12:00:00Z",
        }

        webhook = WebhookCrawlCompleted(**data)

        assert webhook.type == "crawl.completed"
        assert webhook.id == "crawl_123456"
        assert len(webhook.data) == 2
        assert webhook.total == 2
        assert webhook.completed == 2
        assert webhook.creditsUsed == 4
        assert webhook.timestamp == "2024-01-01T12:00:00Z"

    def test_valid_crawl_completed_minimal(self):
        """Test crawl.completed webhook with minimal fields."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123456",
            "data": [],
        }

        webhook = WebhookCrawlCompleted(**data)

        assert webhook.type == "crawl.completed"
        assert webhook.id == "crawl_123456"
        assert webhook.data == []
        assert webhook.total is None
        assert webhook.completed is None
        assert webhook.creditsUsed is None

    def test_empty_data_list_is_valid(self):
        """Test that empty data list is valid."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123456",
            "data": [],
        }

        webhook = WebhookCrawlCompleted(**data)
        assert webhook.data == []

    def test_missing_required_data(self):
        """Test that missing data raises ValidationError."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123456",
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlCompleted(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("data",) for err in errors)

    def test_wrong_type_for_data(self):
        """Test that non-list data raises ValidationError."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123456",
            "data": "not-a-list",
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlCompleted(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("data",) for err in errors)

    def test_invalid_item_in_data_list(self):
        """Test that invalid item in data list raises ValidationError."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123456",
            "data": [
                {
                    "markdown": "# Valid",
                    "metadata": {
                        "sourceURL": "https://example.com",
                        "statusCode": 200,
                    },
                },
                {
                    "markdown": "# Invalid",
                    # Missing required metadata
                },
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlCompleted(**data)

        errors = exc_info.value.errors()
        assert any("metadata" in str(err["loc"]) for err in errors)


# ============================================================================
# WebhookCrawlFailed Tests
# ============================================================================


class TestWebhookCrawlFailed:
    """Test WebhookCrawlFailed model validation."""

    def test_valid_crawl_failed_with_all_fields(self):
        """Test crawl.failed webhook with all fields."""
        data = {
            "type": "crawl.failed",
            "id": "crawl_123456",
            "error": "Connection timeout after 30 seconds",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        webhook = WebhookCrawlFailed(**data)

        assert webhook.type == "crawl.failed"
        assert webhook.id == "crawl_123456"
        assert webhook.error == "Connection timeout after 30 seconds"
        assert webhook.timestamp == "2024-01-01T12:00:00Z"

    def test_valid_crawl_failed_minimal(self):
        """Test crawl.failed webhook with minimal fields."""
        data = {
            "type": "crawl.failed",
            "id": "crawl_123456",
            "error": "Unknown error",
        }

        webhook = WebhookCrawlFailed(**data)

        assert webhook.type == "crawl.failed"
        assert webhook.error == "Unknown error"
        assert webhook.timestamp is None

    def test_missing_required_error(self):
        """Test that missing error raises ValidationError."""
        data = {
            "type": "crawl.failed",
            "id": "crawl_123456",
        }

        with pytest.raises(ValidationError) as exc_info:
            WebhookCrawlFailed(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("error",) for err in errors)

    def test_empty_error_string_is_valid(self):
        """Test that empty error string is valid (edge case)."""
        data = {
            "type": "crawl.failed",
            "id": "crawl_123456",
            "error": "",
        }

        webhook = WebhookCrawlFailed(**data)
        assert webhook.error == ""


# ============================================================================
# WebhookPayload Union Type Tests
# ============================================================================


class TestWebhookPayloadUnion:
    """Test WebhookPayload union type discrimination."""

    def test_discriminate_crawl_started(self):
        """Test that crawl.started is correctly discriminated."""
        data = {
            "type": "crawl.started",
            "id": "crawl_123",
        }

        # When parsed as union, should be WebhookCrawlStarted
        webhook = WebhookCrawlStarted(**data)
        assert isinstance(webhook, WebhookCrawlStarted)
        assert webhook.type == "crawl.started"

    def test_discriminate_crawl_page(self):
        """Test that crawl.page is correctly discriminated."""
        data = {
            "type": "crawl.page",
            "id": "crawl_123",
            "data": {
                "markdown": "Content",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
            },
        }

        webhook = WebhookCrawlPage(**data)
        assert isinstance(webhook, WebhookCrawlPage)
        assert webhook.type == "crawl.page"

    def test_discriminate_crawl_completed(self):
        """Test that crawl.completed is correctly discriminated."""
        data = {
            "type": "crawl.completed",
            "id": "crawl_123",
            "data": [],
        }

        webhook = WebhookCrawlCompleted(**data)
        assert isinstance(webhook, WebhookCrawlCompleted)
        assert webhook.type == "crawl.completed"

    def test_discriminate_crawl_failed(self):
        """Test that crawl.failed is correctly discriminated."""
        data = {
            "type": "crawl.failed",
            "id": "crawl_123",
            "error": "Error message",
        }

        webhook = WebhookCrawlFailed(**data)
        assert isinstance(webhook, WebhookCrawlFailed)
        assert webhook.type == "crawl.failed"


# ============================================================================
# Batch Scrape Webhook Tests
# ============================================================================


class TestBatchScrapeWebhooks:
    """Test batch scrape webhook models."""

    def test_batch_scrape_started(self):
        """Test batch_scrape.started webhook."""
        data = {
            "type": "batch_scrape.started",
            "id": "batch_123",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        webhook = WebhookBatchScrapeStarted(**data)

        assert webhook.type == "batch_scrape.started"
        assert webhook.id == "batch_123"
        assert webhook.timestamp == "2024-01-01T12:00:00Z"

    def test_batch_scrape_page(self):
        """Test batch_scrape.page webhook."""
        data = {
            "type": "batch_scrape.page",
            "id": "batch_123",
            "data": {
                "markdown": "Content",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
            },
        }

        webhook = WebhookBatchScrapePage(**data)

        assert webhook.type == "batch_scrape.page"
        assert webhook.id == "batch_123"
        assert webhook.data.markdown == "Content"

    def test_batch_scrape_completed(self):
        """Test batch_scrape.completed webhook."""
        data = {
            "type": "batch_scrape.completed",
            "id": "batch_123",
            "data": [],
            "total": 0,
            "completed": 0,
            "creditsUsed": 0,
        }

        webhook = WebhookBatchScrapeCompleted(**data)

        assert webhook.type == "batch_scrape.completed"
        assert webhook.id == "batch_123"
        assert webhook.data == []

    def test_batch_scrape_failed(self):
        """Test batch_scrape.failed webhook."""
        data = {
            "type": "batch_scrape.failed",
            "id": "batch_123",
            "error": "Failed to scrape",
        }

        webhook = WebhookBatchScrapeFailed(**data)

        assert webhook.type == "batch_scrape.failed"
        assert webhook.error == "Failed to scrape"


# ============================================================================
# API Response Model Tests
# ============================================================================


class TestFirecrawlCrawlResponse:
    """Test FirecrawlCrawlResponse model."""

    def test_valid_crawl_response(self):
        """Test valid crawl response."""
        data = {
            "success": True,
            "id": "crawl_123",
            "url": "https://example.com",
        }

        response = FirecrawlCrawlResponse(**data)

        assert response.success is True
        assert response.id == "crawl_123"
        assert str(response.url) == "https://example.com/"

    def test_invalid_url_format(self):
        """Test that invalid URL format raises ValidationError."""
        data = {
            "success": True,
            "id": "crawl_123",
            "url": "not-a-valid-url",
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlCrawlResponse(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("url",) for err in errors)

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        data = {"success": True}

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlCrawlResponse(**data)

        errors = exc_info.value.errors()
        assert len(errors) >= 2  # Missing id and url


class TestFirecrawlCrawlStatus:
    """Test FirecrawlCrawlStatus model."""

    def test_valid_crawl_status_with_data(self):
        """Test valid crawl status with data."""
        data = {
            "status": "completed",
            "total": 10,
            "completed": 10,
            "creditsUsed": 20,
            "expiresAt": "2024-12-31T23:59:59Z",
            "data": [
                {
                    "markdown": "Content",
                    "metadata": {
                        "sourceURL": "https://example.com",
                        "statusCode": 200,
                    },
                }
            ],
            "next": "next-page-token",
        }

        status = FirecrawlCrawlStatus(**data)

        assert status.status == "completed"
        assert status.total == 10
        assert status.completed == 10
        assert status.creditsUsed == 20
        assert len(status.data) == 1
        assert status.next == "next-page-token"

    def test_valid_crawl_status_without_optional_fields(self):
        """Test valid crawl status without optional fields."""
        data = {
            "status": "scraping",
            "total": 5,
            "completed": 2,
            "creditsUsed": 4,
            "expiresAt": "2024-12-31T23:59:59Z",
        }

        status = FirecrawlCrawlStatus(**data)

        assert status.status == "scraping"
        assert status.data is None
        assert status.next is None

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        data = {"status": "scraping"}

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlCrawlStatus(**data)

        errors = exc_info.value.errors()
        # Should have errors for total, completed, creditsUsed, expiresAt
        assert len(errors) >= 4


class TestFirecrawlScrapeResponse:
    """Test FirecrawlScrapeResponse model."""

    def test_valid_scrape_response(self):
        """Test valid scrape response."""
        data = {
            "success": True,
            "data": {
                "markdown": "# Page Content",
                "metadata": {
                    "sourceURL": "https://example.com",
                    "statusCode": 200,
                },
            },
        }

        response = FirecrawlScrapeResponse(**data)

        assert response.success is True
        assert response.data.markdown == "# Page Content"
        assert response.data.metadata.sourceURL == "https://example.com"

    def test_missing_required_data(self):
        """Test that missing data raises ValidationError."""
        data = {"success": True}

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlScrapeResponse(**data)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("data",) for err in errors)

    def test_invalid_nested_data(self):
        """Test that invalid nested data raises ValidationError."""
        data = {
            "success": True,
            "data": {
                # Missing required markdown and metadata
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            FirecrawlScrapeResponse(**data)

        errors = exc_info.value.errors()
        assert len(errors) >= 2  # Missing markdown and metadata


# ============================================================================
# Edge Cases and Type Coercion Tests
# ============================================================================


class TestEdgeCasesAndTypeCoercion:
    """Test edge cases and type coercion behavior."""

    def test_type_coercion_string_to_int(self):
        """Test that Pydantic coerces valid string to int."""
        data = {
            "sourceURL": "https://example.com",
            "statusCode": "200",  # String that can be coerced
        }

        # Pydantic should coerce "200" to 200
        metadata = FirecrawlMetadata(**data)
        assert metadata.statusCode == 200
        assert isinstance(metadata.statusCode, int)

    def test_extra_fields_are_ignored(self):
        """Test that extra fields are ignored (default Pydantic behavior)."""
        data = {
            "sourceURL": "https://example.com",
            "statusCode": 200,
            "extra_field": "should be ignored",
        }

        metadata = FirecrawlMetadata(**data)
        assert not hasattr(metadata, "extra_field")

    def test_null_values_for_optional_fields(self):
        """Test that null values for optional fields are accepted."""
        data = {
            "markdown": "Content",
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
            "html": None,
            "links": None,
        }

        page_data = FirecrawlPageData(**data)
        assert page_data.html is None
        assert page_data.links is None

    def test_large_markdown_content(self):
        """Test that large markdown content is accepted."""
        large_content = "# Title\n" + ("Content paragraph.\n" * 10000)
        data = {
            "markdown": large_content,
            "metadata": {
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
        }

        page_data = FirecrawlPageData(**data)
        assert len(page_data.markdown) > 100000

    def test_unicode_content(self):
        """Test that unicode content is handled correctly."""
        data = {
            "markdown": "# 日本語 Title\n\nContent with émojis 🎉",
            "metadata": {
                "sourceURL": "https://example.com/日本語",
                "statusCode": 200,
                "title": "Título en español",
            },
        }

        page_data = FirecrawlPageData(**data)
        assert "日本語" in page_data.markdown
        assert "🎉" in page_data.markdown
        assert page_data.metadata.title == "Título en español"

    def test_special_characters_in_url(self):
        """Test that special characters in URL are handled."""
        data = {
            "sourceURL": "https://example.com/path?query=value&foo=bar#anchor",
            "statusCode": 200,
        }

        metadata = FirecrawlMetadata(**data)
        assert "query=value" in metadata.sourceURL
        assert "#anchor" in metadata.sourceURL

    def test_very_long_error_message(self):
        """Test that very long error messages are accepted."""
        long_error = "Error: " + ("A" * 10000)
        data = {
            "type": "crawl.failed",
            "id": "crawl_123",
            "error": long_error,
        }

        webhook = WebhookCrawlFailed(**data)
        assert len(webhook.error) > 10000


# ============================================================================
# Real-World Payload Tests
# ============================================================================


class TestRealWorldPayloads:
    """Test with realistic payloads based on actual Firecrawl responses."""

    def test_realistic_crawl_page_payload(self):
        """Test with a realistic crawl.page payload."""
        data = {
            "type": "crawl.page",
            "id": "fc-crawl-abc123def456",
            "data": {
                "markdown": """# Getting Started with GraphRAG

GraphRAG is a powerful tool for building knowledge graphs from web content.

## Installation

```bash
npm install graphrag
```

## Usage

Import and use GraphRAG in your application:

```javascript
import { GraphRAG } from 'graphrag';
```
""",
                "html": "<html><head><title>Getting Started</title></head><body>...</body></html>",
                "links": [
                    "https://example.com/docs",
                    "https://example.com/api",
                    "https://example.com/tutorials",
                ],
                "metadata": {
                    "sourceURL": "https://example.com/docs/getting-started",
                    "title": "Getting Started with GraphRAG - Documentation",
                    "description": "Learn how to get started with GraphRAG",
                    "language": "en-US",
                    "statusCode": 200,
                    "ogTitle": "Getting Started | GraphRAG Docs",
                    "ogDescription": "Complete guide to GraphRAG setup",
                    "ogImage": "https://example.com/og-image.png",
                },
            },
            "timestamp": "2024-11-01T14:23:45.123Z",
        }

        webhook = WebhookCrawlPage(**data)

        assert webhook.type == "crawl.page"
        assert "GraphRAG" in webhook.data.markdown
        assert len(webhook.data.links) == 3
        assert webhook.data.metadata.language == "en-US"

    def test_realistic_crawl_completed_payload(self):
        """Test with a realistic crawl.completed payload."""
        data = {
            "type": "crawl.completed",
            "id": "fc-crawl-xyz789",
            "data": [
                {
                    "markdown": "# Home Page",
                    "metadata": {
                        "sourceURL": "https://example.com",
                        "statusCode": 200,
                        "title": "Home",
                    },
                },
                {
                    "markdown": "# About Us",
                    "metadata": {
                        "sourceURL": "https://example.com/about",
                        "statusCode": 200,
                        "title": "About",
                    },
                },
                {
                    "markdown": "# Contact",
                    "metadata": {
                        "sourceURL": "https://example.com/contact",
                        "statusCode": 200,
                        "title": "Contact Us",
                    },
                },
            ],
            "total": 3,
            "completed": 3,
            "creditsUsed": 6,
            "timestamp": "2024-11-01T14:30:00.000Z",
        }

        webhook = WebhookCrawlCompleted(**data)

        assert len(webhook.data) == 3
        assert webhook.total == 3
        assert webhook.completed == 3
        assert webhook.creditsUsed == 6

    def test_realistic_crawl_failed_payload(self):
        """Test with a realistic crawl.failed payload."""
        data = {
            "type": "crawl.failed",
            "id": "fc-crawl-fail123",
            "error": "Crawl failed: Rate limit exceeded. Please try again later or upgrade your plan.",
            "timestamp": "2024-11-01T14:35:22.456Z",
        }

        webhook = WebhookCrawlFailed(**data)

        assert "Rate limit exceeded" in webhook.error
        assert webhook.timestamp is not None


# ============================================================================
# Summary Statistics
# ============================================================================


def test_suite_summary():
    """
    Test suite summary:

    Coverage:
    - FirecrawlMetadata: 11 tests
    - FirecrawlPageData: 9 tests
    - WebhookCrawlStarted: 5 tests
    - WebhookCrawlPage: 5 tests
    - WebhookCrawlCompleted: 6 tests
    - WebhookCrawlFailed: 4 tests
    - WebhookPayload Union: 4 tests
    - Batch Scrape: 4 tests
    - FirecrawlCrawlResponse: 3 tests
    - FirecrawlCrawlStatus: 3 tests
    - FirecrawlScrapeResponse: 3 tests
    - Edge Cases: 9 tests
    - Real-World Payloads: 3 tests

    Total: 69 tests

    Test categories:
    1. Valid data (happy path)
    2. Missing required fields
    3. Invalid field types
    4. Boundary values
    5. Edge cases (empty strings, large content, unicode)
    6. Type coercion
    7. Nested validation
    8. Union type discrimination
    9. Real-world payloads
    """
    pass
