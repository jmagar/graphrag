"""
Pydantic models for Firecrawl v2 API data structures.
"""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, HttpUrl


class FirecrawlMetadata(BaseModel):
    """Metadata from a crawled page."""

    sourceURL: str = Field(..., description="The URL of the crawled page")
    title: Optional[str] = Field(None, description="Page title")
    description: Optional[str] = Field(None, description="Page description")
    language: Optional[str] = Field(None, description="Page language code")
    statusCode: int = Field(..., description="HTTP status code", ge=100, le=599)
    ogTitle: Optional[str] = Field(None, description="Open Graph title")
    ogDescription: Optional[str] = Field(None, description="Open Graph description")
    ogImage: Optional[str] = Field(None, description="Open Graph image URL")
    ogUrl: Optional[str] = Field(None, description="Open Graph canonical URL")


class FirecrawlPageData(BaseModel):
    """Data from a single crawled page."""

    markdown: str = Field(..., description="Page content as markdown")
    html: Optional[str] = Field(None, description="Raw HTML content")
    rawHtml: Optional[str] = Field(None, description="Unprocessed HTML content")
    links: Optional[List[str]] = Field(None, description="Outgoing links from the page")
    metadata: FirecrawlMetadata = Field(..., description="Page metadata")
    screenshot: Optional[str] = Field(None, description="Base64 encoded screenshot")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Browser actions performed")


class WebhookCrawlStarted(BaseModel):
    """Webhook payload for crawl.started event."""

    type: Literal["crawl.started"] = "crawl.started"
    id: str = Field(..., description="Crawl job ID")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class WebhookCrawlPage(BaseModel):
    """Webhook payload for crawl.page event."""

    type: Literal["crawl.page"] = "crawl.page"
    id: str = Field(..., description="Crawl job ID")
    data: FirecrawlPageData = Field(..., description="Crawled page data")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class WebhookCrawlCompleted(BaseModel):
    """Webhook payload for crawl.completed event."""

    type: Literal["crawl.completed"] = "crawl.completed"
    id: str = Field(..., description="Crawl job ID")
    data: List[FirecrawlPageData] = Field(..., description="All crawled pages")
    total: Optional[int] = Field(None, description="Total pages crawled")
    completed: Optional[int] = Field(None, description="Completed pages")
    creditsUsed: Optional[int] = Field(None, description="Credits consumed")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class WebhookCrawlFailed(BaseModel):
    """Webhook payload for crawl.failed event."""

    type: Literal["crawl.failed"] = "crawl.failed"
    id: str = Field(..., description="Crawl job ID")
    error: str = Field(..., description="Error message")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


# Union type for all webhook payloads
WebhookPayload = Union[
    WebhookCrawlStarted,
    WebhookCrawlPage,
    WebhookCrawlCompleted,
    WebhookCrawlFailed,
]


# Batch scrape models
class WebhookBatchScrapeStarted(BaseModel):
    """Webhook payload for batch_scrape.started event."""

    type: Literal["batch_scrape.started"] = "batch_scrape.started"
    id: str = Field(..., description="Batch job ID")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class WebhookBatchScrapePage(BaseModel):
    """Webhook payload for batch_scrape.page event."""

    type: Literal["batch_scrape.page"] = "batch_scrape.page"
    id: str = Field(..., description="Batch job ID")
    data: FirecrawlPageData = Field(..., description="Scraped page data")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class WebhookBatchScrapeCompleted(BaseModel):
    """Webhook payload for batch_scrape.completed event."""

    type: Literal["batch_scrape.completed"] = "batch_scrape.completed"
    id: str = Field(..., description="Batch job ID")
    data: List[FirecrawlPageData] = Field(..., description="All scraped pages")
    total: Optional[int] = Field(None, description="Total pages")
    completed: Optional[int] = Field(None, description="Completed pages")
    creditsUsed: Optional[int] = Field(None, description="Credits consumed")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


class WebhookBatchScrapeFailed(BaseModel):
    """Webhook payload for batch_scrape.failed event."""

    type: Literal["batch_scrape.failed"] = "batch_scrape.failed"
    id: str = Field(..., description="Batch job ID")
    error: str = Field(..., description="Error message")
    timestamp: Optional[str] = Field(None, description="Event timestamp")


# Response models for API endpoints
class CrawlStatusEnum(str):
    """Enum for crawl status values."""

    SCRAPING = "scraping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FirecrawlCrawlResponse(BaseModel):
    """Response from starting a crawl."""

    success: bool
    id: str = Field(..., description="Crawl job ID")
    url: HttpUrl = Field(..., description="URL being crawled")


class FirecrawlCrawlStatus(BaseModel):
    """Status response for a crawl job."""

    status: str = Field(..., description="Current crawl status")
    total: int = Field(..., description="Total pages discovered")
    completed: int = Field(..., description="Pages completed")
    creditsUsed: int = Field(..., description="Credits consumed")
    expiresAt: str = Field(..., description="When results expire")
    data: Optional[List[FirecrawlPageData]] = Field(None, description="Crawled pages")
    next: Optional[str] = Field(None, description="Pagination token")


class FirecrawlScrapeResponse(BaseModel):
    """Response from scraping a URL."""

    success: bool
    data: FirecrawlPageData = Field(..., description="Scraped page data")
