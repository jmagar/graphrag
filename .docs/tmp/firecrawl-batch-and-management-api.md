# Firecrawl v2 Batch Scraping and Crawl Management API

## Complete API Reference

This document provides comprehensive documentation for Firecrawl v2's batch scraping, crawl management, and monitoring endpoints.

---

## Table of Contents

1. [Batch Scrape Operations](#batch-scrape-operations)
2. [Batch Scrape Status & Monitoring](#batch-scrape-status--monitoring)
3. [Crawl Management](#crawl-management)
4. [Crawl Status & Monitoring](#crawl-status--monitoring)
5. [Error Handling](#error-handling)
6. [Active Jobs Management](#active-jobs-management)
7. [Crawl Params Preview](#crawl-params-preview)
8. [Webhook Integration](#webhook-integration)
9. [Implementation Patterns](#implementation-patterns)
10. [Response Schemas](#response-schemas)

---

## 1. Batch Scrape Operations

### POST /v2/batch/scrape

Scrape multiple URLs simultaneously with optional extraction and webhook notifications.

**Endpoint:** `https://api.firecrawl.dev/v2/batch/scrape`

**Authentication:** Bearer token in Authorization header

#### Request Schema

```typescript
interface BatchScrapeRequest {
  urls: string[];                    // Required: Array of URLs to scrape
  webhook?: WebhookConfig;           // Optional: Webhook configuration
  maxConcurrency?: number;           // Optional: Concurrent scrape limit
  ignoreInvalidURLs?: boolean;       // Default: true

  // Scrape options (apply to all URLs)
  formats?: Format[];                // Output formats
  onlyMainContent?: boolean;         // Default: true
  includeTags?: string[];            // HTML tags to include
  excludeTags?: string[];            // HTML tags to exclude
  maxAge?: number;                   // Cache age in ms (default: 172800000)
  headers?: Record<string, string>;  // Custom HTTP headers
  waitFor?: number;                  // Delay in ms before scraping
  mobile?: boolean;                  // Emulate mobile device
  skipTlsVerification?: boolean;     // Default: true
  timeout?: number;                  // Request timeout in ms
  parsers?: ('pdf')[];               // File parsers
  actions?: Action[];                // Pre-scrape actions
  location?: LocationConfig;         // Geographic location settings
  removeBase64Images?: boolean;      // Default: true
  blockAds?: boolean;                // Default: true
  proxy?: 'basic' | 'stealth' | 'auto'; // Default: 'auto'
  storeInCache?: boolean;            // Default: true
  zeroDataRetention?: boolean;       // Default: false
}

interface WebhookConfig {
  url: string;                       // Webhook endpoint URL (HTTPS recommended)
  headers?: Record<string, string>;  // Custom headers for webhook requests
  metadata?: Record<string, any>;    // Custom metadata in webhook payload
  events?: string[];                 // Event types to receive
}

type Format =
  | 'markdown'
  | 'html'
  | 'rawHtml'
  | 'links'
  | 'screenshot'
  | { type: 'json', schema: any };

interface Action {
  type: 'wait' | 'screenshot' | 'click' | 'write' | 'press' | 'scroll' | 'scrape' | 'execute' | 'pdf';
  // Type-specific properties
}

interface LocationConfig {
  country?: string;                  // Country code (e.g., "US")
  languages?: string[];              // Language codes (e.g., ["en-US"])
}
```

#### Response Schema

```typescript
interface BatchScrapeStartResponse {
  success: boolean;
  id: string;                        // UUID for status tracking
  url: string;                       // Status endpoint URL
  invalidURLs?: string[] | null;     // Invalid URLs (if ignoreInvalidURLs: true)
}
```

#### Example Request

```bash
curl -X POST https://api.firecrawl.dev/v2/batch/scrape \
  -H 'Authorization: Bearer fc-YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "urls": [
      "https://example.com/page1",
      "https://example.com/page2",
      "https://example.com/page3"
    ],
    "formats": ["markdown", "html"],
    "onlyMainContent": true,
    "maxConcurrency": 5,
    "webhook": {
      "url": "https://your-domain.com/webhook",
      "metadata": {
        "batchId": "user-batch-123"
      },
      "events": ["started", "page", "completed", "failed"]
    }
  }'
```

#### Example Response

```json
{
  "success": true,
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "url": "https://api.firecrawl.dev/v2/batch/scrape/123e4567-e89b-12d3-a456-426614174000",
  "invalidURLs": []
}
```

---

## 2. Batch Scrape Status & Monitoring

### GET /v2/batch/scrape/{id}

Check the status of a batch scrape job and retrieve results.

**Endpoint:** `https://api.firecrawl.dev/v2/batch/scrape/{id}`

**Authentication:** Bearer token in Authorization header

#### Path Parameters

- `id` (string, UUID, required): Batch scrape job ID

#### Response Schema

```typescript
interface BatchScrapeStatusResponse {
  status: 'scraping' | 'completed' | 'failed';
  total: number;                     // Total URLs attempted
  completed: number;                 // Successfully scraped URLs
  creditsUsed: number;               // Credits consumed
  expiresAt: string;                 // ISO 8601 timestamp (24hr expiry)
  next?: string | null;              // Pagination URL for next 10MB chunk
  data?: ScrapedPage[];              // Scraped page data
}

interface ScrapedPage {
  markdown?: string;                 // Markdown content
  html?: string;                     // HTML content
  rawHtml?: string;                  // Raw HTML
  links?: string[];                  // Extracted links
  screenshot?: string;               // Screenshot base64
  json?: any;                        // Structured data (if schema provided)
  metadata: PageMetadata;
}

interface PageMetadata {
  title?: string;
  language?: string;
  sourceURL: string;
  description?: string;
  ogLocaleAlternate?: string[];
  statusCode: number;
}
```

#### Pagination Handling

**Important:** Batch scrape results expire after **24 hours**. For large responses:

1. Check if `next` field is present in response
2. If present, make GET request to `next` URL to retrieve next chunk
3. Continue until `next` is `null`
4. Each chunk is limited to 10MB

#### Example Request

```bash
curl -X GET https://api.firecrawl.dev/v2/batch/scrape/123e4567-e89b-12d3-a456-426614174000 \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

#### Example Response (In Progress)

```json
{
  "status": "scraping",
  "total": 50,
  "completed": 23,
  "creditsUsed": 23,
  "expiresAt": "2025-10-31T10:30:00.000Z"
}
```

#### Example Response (Completed)

```json
{
  "status": "completed",
  "total": 50,
  "completed": 50,
  "creditsUsed": 50,
  "expiresAt": "2025-10-31T10:30:00.000Z",
  "next": "https://api.firecrawl.dev/v2/batch/scrape/123e4567-e89b-12d3-a456-426614174000?skip=26",
  "data": [
    {
      "markdown": "# Page Title\n\nPage content...",
      "html": "<!DOCTYPE html>...",
      "metadata": {
        "title": "Example Page",
        "language": "en",
        "sourceURL": "https://example.com/page1",
        "statusCode": 200
      }
    }
  ]
}
```

---

## 3. Crawl Management

### DELETE /v2/crawl/{id}

Cancel an active crawl job.

**Endpoint:** `https://api.firecrawl.dev/v2/crawl/{id}`

**Authentication:** Bearer token in Authorization header

#### Path Parameters

- `id` (string, UUID, required): Crawl job ID

#### Response Schema

```typescript
interface CrawlCancelResponse {
  status: 'cancelled';
}
```

#### Example Request

```bash
curl -X DELETE https://api.firecrawl.dev/v2/crawl/123e4567-e89b-12d3-a456-426614174000 \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

#### Example Response

```json
{
  "status": "cancelled"
}
```

### DELETE /v2/batch/scrape/{id}

Cancel an active batch scrape job.

**Endpoint:** `https://api.firecrawl.dev/v2/batch/scrape/{id}`

**Authentication:** Bearer token in Authorization header

#### Path Parameters

- `id` (string, UUID, required): Batch scrape job ID

#### Response Schema

```typescript
interface BatchScrapeCancelResponse {
  success: boolean;
  message: string;
}
```

#### Example Request

```bash
curl -X DELETE https://api.firecrawl.dev/v2/batch/scrape/123e4567-e89b-12d3-a456-426614174000 \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

#### Example Response

```json
{
  "success": true,
  "message": "Batch scrape job successfully cancelled."
}
```

---

## 4. Crawl Status & Monitoring

### GET /v2/crawl/{id}

Check the status of a crawl job and retrieve results.

**Endpoint:** `https://api.firecrawl.dev/v2/crawl/{id}`

**Authentication:** Bearer token in Authorization header

#### Path Parameters

- `id` (string, UUID, required): Crawl job ID

#### Response Schema

```typescript
interface CrawlStatusResponse {
  status: 'scraping' | 'completed' | 'failed';
  total: number;                     // Total pages attempted
  completed: number;                 // Successfully crawled pages
  creditsUsed: number;               // Credits consumed
  expiresAt: string;                 // ISO 8601 timestamp
  next?: string | null;              // Pagination URL for next 10MB chunk
  data?: CrawledPage[];              // Crawled page data
}

interface CrawledPage {
  markdown?: string;
  html?: string;
  rawHtml?: string;
  links?: string[];
  screenshot?: string;
  json?: any;
  metadata: PageMetadata;
}
```

#### Example Request

```bash
curl -X GET https://api.firecrawl.dev/v2/crawl/123e4567-e89b-12d3-a456-426614174000 \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

#### Example Response

```json
{
  "status": "scraping",
  "total": 150,
  "completed": 87,
  "creditsUsed": 87,
  "expiresAt": "2025-10-31T10:30:00.000Z"
}
```

---

## 5. Error Handling

### GET /v2/crawl/{id}/errors

Retrieve detailed error information for a crawl job.

**Endpoint:** `https://api.firecrawl.dev/v2/crawl/{id}/errors`

**Authentication:** Bearer token in Authorization header

#### Path Parameters

- `id` (string, UUID, required): Crawl job ID

#### Response Schema

```typescript
interface CrawlErrorsResponse {
  errors: ErrorDetail[];
  robotsBlocked: string[];           // URLs blocked by robots.txt
}

interface ErrorDetail {
  id: string;                        // Error ID
  timestamp: string;                 // ISO 8601 timestamp
  url: string;                       // URL that failed
  error: string;                     // Error message
}
```

#### Example Request

```bash
curl -X GET https://api.firecrawl.dev/v2/crawl/123e4567-e89b-12d3-a456-426614174000/errors \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

#### Example Response

```json
{
  "errors": [
    {
      "id": "err_123",
      "timestamp": "2025-10-30T14:23:45.000Z",
      "url": "https://example.com/protected",
      "error": "SCRAPE_ALL_ENGINES_FAILED"
    },
    {
      "id": "err_124",
      "timestamp": "2025-10-30T14:24:12.000Z",
      "url": "https://example.com/ssl-error",
      "error": "SCRAPE_SSL_ERROR"
    }
  ],
  "robotsBlocked": [
    "https://example.com/admin",
    "https://example.com/private"
  ]
}
```

### GET /v2/batch/scrape/{id}/errors

Retrieve detailed error information for a batch scrape job.

**Endpoint:** `https://api.firecrawl.dev/v2/batch/scrape/{id}/errors`

**Authentication:** Bearer token in Authorization header

#### Path Parameters

- `id` (string, UUID, required): Batch scrape job ID

#### Response Schema

Same as crawl errors response.

#### Example Request

```bash
curl -X GET https://api.firecrawl.dev/v2/batch/scrape/123e4567-e89b-12d3-a456-426614174000/errors \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

### Common Error Codes

| Error Code | Status | Description |
|------------|--------|-------------|
| `SCRAPE_ALL_ENGINES_FAILED` | 500 | All scraping engines failed |
| `SCRAPE_SSL_ERROR` | 500 | Invalid SSL certificate (use `skipTlsVerification: true`) |
| `SCRAPE_SITE_ERROR` | 500 | Unrecoverable site error |
| `SCRAPE_DNS_RESOLUTION_ERROR` | 500 | DNS resolution failed |
| `SCRAPE_ACTION_ERROR` | 500 | Error performing page action |
| `SCRAPE_PDF_PREFETCH_FAILED` | 500 | Failed to prefetch PDF |
| `SCRAPE_PDF_INSUFFICIENT_TIME_ERROR` | 500 | Not enough time to process PDF |
| `SCRAPE_PDF_ANTIBOT_ERROR` | 500 | PDF blocked by anti-bot |
| `SCRAPE_ZDR_VIOLATION_ERROR` | 500 | Zero data retention conflict |
| `SCRAPE_UNSUPPORTED_FILE_ERROR` | 500 | Unsupported file type |
| `UNKNOWN_ERROR` | 500 | Generic or unexpected error |

---

## 6. Active Jobs Management

### GET /v2/crawl/active

List all currently active crawl jobs for your account.

**Endpoint:** `https://api.firecrawl.dev/v2/crawl/active`

**Authentication:** Bearer token in Authorization header

#### Response Schema

```typescript
interface ActiveCrawlsResponse {
  success: boolean;
  crawls: ActiveCrawl[];
}

interface ActiveCrawl {
  id: string;                        // Crawl job UUID
  teamId: string;                    // Team identifier
  url: string;                       // Starting URL
  options: CrawlOptions;             // Crawl configuration
}

interface CrawlOptions {
  scrapeOptions?: {
    formats?: string[];
    onlyMainContent?: boolean;
    includeTags?: string[];
    excludeTags?: string[];
    maxAge?: number;
    headers?: Record<string, string>;
    waitFor?: number;
    mobile?: boolean;
    skipTlsVerification?: boolean;
    timeout?: number;
    parsers?: string[];
    actions?: Action[];
    location?: LocationConfig;
    removeBase64Images?: boolean;
    blockAds?: boolean;
    proxy?: string;
    storeInCache?: boolean;
  };
}
```

#### Example Request

```bash
curl -X GET https://api.firecrawl.dev/v2/crawl/active \
  -H 'Authorization: Bearer fc-YOUR_API_KEY'
```

#### Example Response

```json
{
  "success": true,
  "crawls": [
    {
      "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
      "teamId": "team_123",
      "url": "https://docs.example.com",
      "options": {
        "scrapeOptions": {
          "formats": ["markdown"],
          "onlyMainContent": true,
          "maxAge": 172800000,
          "mobile": false,
          "skipTlsVerification": true,
          "removeBase64Images": true,
          "blockAds": true,
          "proxy": "auto",
          "storeInCache": true
        }
      }
    }
  ]
}
```

---

## 7. Crawl Params Preview

### POST /v2/crawl/params-preview

Preview crawl parameters derived from natural language prompts before starting a crawl.

**Endpoint:** `https://api.firecrawl.dev/v2/crawl/params-preview`

**Authentication:** Bearer token in Authorization header

#### Request Schema

```typescript
interface ParamsPreviewRequest {
  url: string;                       // Required: Starting URL
  prompt: string;                    // Required: Natural language crawl description (max 10,000 chars)
}
```

#### Response Schema

```typescript
interface ParamsPreviewResponse {
  success: boolean;
  data: {
    url: string;                     // Starting URL
    prompt: string;                  // Original prompt
    includePaths?: string[];         // Derived include patterns
    excludePaths?: string[];         // Derived exclude patterns
    maxDepth?: number;               // Derived max crawl depth
    maxDiscoveryDepth?: number;      // Derived max discovery depth
    crawlEntireDomain?: boolean;     // Whether to crawl entire domain
    allowExternalLinks?: boolean;    // Whether to follow external links
    allowSubdomains?: boolean;       // Whether to crawl subdomains
    sitemap?: 'include' | 'only' | 'skip';
    ignoreQueryParameters?: boolean;
    deduplicateSimilarURLs?: boolean;
    delay?: number;                  // Delay between requests (ms)
    limit?: number;                  // Max pages to crawl
  };
}
```

#### Example Request

```bash
curl -X POST https://api.firecrawl.dev/v2/crawl/params-preview \
  -H 'Authorization: Bearer fc-YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://docs.stripe.com",
    "prompt": "Crawl the API documentation but exclude changelog and blog posts"
  }'
```

#### Example Response

```json
{
  "success": true,
  "data": {
    "url": "https://docs.stripe.com",
    "prompt": "Crawl the API documentation but exclude changelog and blog posts",
    "crawlEntireDomain": false,
    "includePaths": ["/api/.*", "/docs/.*"],
    "excludePaths": ["/changelog/.*", "/blog/.*"],
    "sitemap": "include",
    "maxDepth": 5,
    "limit": 500
  }
}
```

---

## 8. Webhook Integration

Webhooks provide real-time notifications as crawls and batch scrapes progress, eliminating the need for polling.

### Webhook Configuration

```typescript
interface WebhookConfig {
  url: string;                       // HTTPS endpoint (required)
  headers?: Record<string, string>;  // Custom headers
  metadata?: Record<string, any>;    // Custom metadata in all payloads
  events?: string[];                 // Events to subscribe to
}
```

### Event Types

#### Crawl Events

- `crawl.started` - Crawl job begins
- `crawl.page` - Each page successfully scraped
- `crawl.completed` - Crawl finishes successfully
- `crawl.failed` - Crawl encounters error

#### Batch Scrape Events

- `batch_scrape.started` - Batch scrape begins
- `batch_scrape.page` - Each URL successfully scraped
- `batch_scrape.completed` - All URLs processed
- `batch_scrape.failed` - Batch scrape encounters error

### Webhook Payload Schema

```typescript
interface WebhookPayload {
  success: boolean;
  type: string;                      // Event type (e.g., "crawl.page")
  id: string;                        // Job ID
  data?: any[];                      // Page data (for 'page' events)
  metadata?: Record<string, any>;    // Custom metadata from request
  error?: string | null;             // Error message (for 'failed' events)
}
```

### Webhook Security

Firecrawl signs every webhook request using HMAC-SHA256.

#### Signature Header

```
X-Firecrawl-Signature: sha256=abc123def456...
```

#### Verification Steps

1. Extract signature from `X-Firecrawl-Signature` header
2. Get raw request body (JSON string, unparsed)
3. Compute HMAC-SHA256 using your secret key
4. Compare signatures using timing-safe comparison
5. Only process if signatures match

#### Example Verification (Node.js)

```typescript
import crypto from 'crypto';

function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expectedSignature = 'sha256=' +
    crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}
```

#### Example Verification (Python)

```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    expected_signature = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
```

### Webhook Best Practices

1. **Always use HTTPS endpoints**
2. **Verify signatures** on every request
3. **Respond quickly** (< 30 seconds with 2xx status)
4. **Process asynchronously** - queue heavy work
5. **Use timing-safe comparisons** for signature verification
6. **Handle retries** - Firecrawl may retry failed webhooks

---

## 9. Implementation Patterns

### Pattern 1: Start and Wait (SDK Methods)

**When to use:** Short batch scrapes or crawls where immediate results are needed.

#### Batch Scrape

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key='fc-YOUR_API_KEY')

# Starts job and waits for completion
result = app.batch_scrape(
    urls=['https://example.com/1', 'https://example.com/2'],
    formats=['markdown', 'html']
)

# Returns full results when complete
for page in result['data']:
    print(f"URL: {page['metadata']['sourceURL']}")
    print(f"Title: {page['metadata']['title']}")
    print(f"Content length: {len(page['markdown'])}")
```

#### Crawl

```python
# Starts crawl and waits for completion
result = app.crawl(
    url='https://docs.example.com',
    params={
        'limit': 100,
        'scrapeOptions': {
            'formats': ['markdown']
        }
    }
)

# Returns full results when complete
for page in result['data']:
    print(f"Crawled: {page['metadata']['sourceURL']}")
```

### Pattern 2: Start and Poll (Manual Status Checking)

**When to use:** Long-running jobs, multiple concurrent jobs, or custom progress tracking.

#### Implementation

```python
import time
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key='fc-YOUR_API_KEY')

# Start batch scrape
response = app.start_batch_scrape(
    urls=['https://example.com/1', 'https://example.com/2'],
    formats=['markdown']
)

job_id = response['id']
print(f"Started batch scrape: {job_id}")

# Poll for status
while True:
    status = app.get_batch_scrape_status(job_id)

    print(f"Status: {status['status']}")
    print(f"Progress: {status['completed']}/{status['total']}")

    if status['status'] in ['completed', 'failed']:
        break

    time.sleep(5)  # Poll every 5 seconds

# Handle results
if status['status'] == 'completed':
    # Process paginated results
    results = []
    next_url = None

    while True:
        if next_url:
            chunk = app.get_batch_scrape_status(job_id)  # Would need next_url param
        else:
            chunk = status

        results.extend(chunk.get('data', []))

        if not chunk.get('next'):
            break

        next_url = chunk['next']

    print(f"Total pages scraped: {len(results)}")
else:
    # Check errors
    errors = app.get_batch_scrape_errors(job_id)
    print(f"Errors: {len(errors['errors'])}")
    for error in errors['errors']:
        print(f"  - {error['url']}: {error['error']}")
```

### Pattern 3: Webhook-Based Processing

**When to use:** Real-time processing, distributed systems, or avoiding polling overhead.

#### Backend Webhook Handler

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()

WEBHOOK_SECRET = "your-webhook-secret"

def verify_signature(payload: str, signature: str) -> bool:
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.post("/api/webhooks/firecrawl")
async def handle_webhook(request: Request):
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get('X-Firecrawl-Signature', '')

    # Verify signature
    if not verify_signature(body.decode(), signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    payload = await request.json()

    # Route based on event type
    event_type = payload['type']

    if event_type == 'batch_scrape.page':
        # Process individual page
        await process_scraped_page(payload['data'][0])
    elif event_type == 'batch_scrape.completed':
        # Handle completion
        await finalize_batch(payload['id'])
    elif event_type == 'batch_scrape.failed':
        # Handle failure
        await handle_batch_failure(payload['id'], payload['error'])

    return {"status": "received"}

async def process_scraped_page(page_data):
    # Your processing logic
    print(f"Processing: {page_data['metadata']['sourceURL']}")
    # Store in database, generate embeddings, etc.
```

#### Starting Batch with Webhook

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key='fc-YOUR_API_KEY')

response = app.start_batch_scrape(
    urls=['https://example.com/1', 'https://example.com/2'],
    formats=['markdown'],
    webhook={
        'url': 'https://your-domain.com/api/webhooks/firecrawl',
        'metadata': {
            'batchId': 'user-batch-123',
            'userId': 'user-456'
        },
        'events': ['started', 'page', 'completed', 'failed']
    }
)

print(f"Started batch with webhook: {response['id']}")
```

### Pattern 4: Active Job Monitoring

**When to use:** Managing multiple concurrent operations, implementing admin dashboards.

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key='fc-YOUR_API_KEY')

# List all active crawls
active_crawls = app.get_active_crawls()

print(f"Active crawls: {len(active_crawls['crawls'])}")

for crawl in active_crawls['crawls']:
    # Check status of each
    status = app.get_crawl_status(crawl['id'])

    print(f"\nCrawl ID: {crawl['id']}")
    print(f"URL: {crawl['url']}")
    print(f"Status: {status['status']}")
    print(f"Progress: {status['completed']}/{status['total']}")

    # Cancel long-running jobs if needed
    if status['total'] > 1000 and status['completed'] < 100:
        print("Cancelling large crawl...")
        app.cancel_crawl(crawl['id'])
```

### Pattern 5: Error Recovery

**When to use:** Handling partial failures, implementing retry logic.

```python
from firecrawl import FirecrawlApp
import time

app = FirecrawlApp(api_key='fc-YOUR_API_KEY')

def batch_scrape_with_retry(urls: list[str], max_retries: int = 3):
    # Start initial batch
    response = app.start_batch_scrape(urls=urls, formats=['markdown'])
    job_id = response['id']

    # Wait for completion
    while True:
        status = app.get_batch_scrape_status(job_id)
        if status['status'] in ['completed', 'failed']:
            break
        time.sleep(5)

    # Check for errors
    if status['status'] == 'failed' or status['completed'] < status['total']:
        errors = app.get_batch_scrape_errors(job_id)

        # Collect failed URLs
        failed_urls = [err['url'] for err in errors['errors']]

        print(f"Failed URLs: {len(failed_urls)}")

        # Retry failed URLs
        if failed_urls and max_retries > 0:
            print(f"Retrying {len(failed_urls)} URLs...")
            return batch_scrape_with_retry(failed_urls, max_retries - 1)

    return status

# Usage
result = batch_scrape_with_retry([
    'https://example.com/1',
    'https://example.com/2',
    'https://example.com/3'
])
```

---

## 10. Response Schemas

### Complete Type Definitions

```typescript
// ============================================================================
// Batch Scrape Types
// ============================================================================

interface BatchScrapeRequest {
  urls: string[];
  webhook?: WebhookConfig;
  maxConcurrency?: number;
  ignoreInvalidURLs?: boolean;
  formats?: Format[];
  onlyMainContent?: boolean;
  includeTags?: string[];
  excludeTags?: string[];
  maxAge?: number;
  headers?: Record<string, string>;
  waitFor?: number;
  mobile?: boolean;
  skipTlsVerification?: boolean;
  timeout?: number;
  parsers?: ('pdf')[];
  actions?: Action[];
  location?: LocationConfig;
  removeBase64Images?: boolean;
  blockAds?: boolean;
  proxy?: 'basic' | 'stealth' | 'auto';
  storeInCache?: boolean;
  zeroDataRetention?: boolean;
}

interface BatchScrapeStartResponse {
  success: boolean;
  id: string;
  url: string;
  invalidURLs?: string[] | null;
}

interface BatchScrapeStatusResponse {
  status: 'scraping' | 'completed' | 'failed';
  total: number;
  completed: number;
  creditsUsed: number;
  expiresAt: string;
  next?: string | null;
  data?: ScrapedPage[];
}

interface BatchScrapeCancelResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// Crawl Types
// ============================================================================

interface CrawlRequest {
  url: string;
  prompt?: string;
  excludePaths?: string[];
  includePaths?: string[];
  maxDiscoveryDepth?: number;
  sitemap?: 'include' | 'only' | 'skip';
  ignoreQueryParameters?: boolean;
  limit?: number;
  crawlEntireDomain?: boolean;
  allowExternalLinks?: boolean;
  allowSubdomains?: boolean;
  delay?: number;
  maxConcurrency?: number;
  webhook?: WebhookConfig;
  scrapeOptions?: ScrapeOptions;
  zeroDataRetention?: boolean;
}

interface CrawlStatusResponse {
  status: 'scraping' | 'completed' | 'failed';
  total: number;
  completed: number;
  creditsUsed: number;
  expiresAt: string;
  next?: string | null;
  data?: CrawledPage[];
}

interface CrawlCancelResponse {
  status: 'cancelled';
}

interface ActiveCrawlsResponse {
  success: boolean;
  crawls: ActiveCrawl[];
}

interface ActiveCrawl {
  id: string;
  teamId: string;
  url: string;
  options: CrawlOptions;
}

// ============================================================================
// Error Types
// ============================================================================

interface ErrorsResponse {
  errors: ErrorDetail[];
  robotsBlocked: string[];
}

interface ErrorDetail {
  id: string;
  timestamp: string;
  url: string;
  error: string;
}

// ============================================================================
// Params Preview Types
// ============================================================================

interface ParamsPreviewRequest {
  url: string;
  prompt: string;
}

interface ParamsPreviewResponse {
  success: boolean;
  data: {
    url: string;
    prompt: string;
    includePaths?: string[];
    excludePaths?: string[];
    maxDepth?: number;
    maxDiscoveryDepth?: number;
    crawlEntireDomain?: boolean;
    allowExternalLinks?: boolean;
    allowSubdomains?: boolean;
    sitemap?: 'include' | 'only' | 'skip';
    ignoreQueryParameters?: boolean;
    deduplicateSimilarURLs?: boolean;
    delay?: number;
    limit?: number;
  };
}

// ============================================================================
// Webhook Types
// ============================================================================

interface WebhookConfig {
  url: string;
  headers?: Record<string, string>;
  metadata?: Record<string, any>;
  events?: string[];
}

interface WebhookPayload {
  success: boolean;
  type: string;
  id: string;
  data?: any[];
  metadata?: Record<string, any>;
  error?: string | null;
}

// ============================================================================
// Shared Types
// ============================================================================

interface ScrapedPage {
  markdown?: string;
  html?: string;
  rawHtml?: string;
  links?: string[];
  screenshot?: string;
  json?: any;
  metadata: PageMetadata;
}

interface CrawledPage {
  markdown?: string;
  html?: string;
  rawHtml?: string;
  links?: string[];
  screenshot?: string;
  json?: any;
  metadata: PageMetadata;
}

interface PageMetadata {
  title?: string;
  language?: string;
  sourceURL: string;
  description?: string;
  ogLocaleAlternate?: string[];
  statusCode: number;
}

type Format =
  | 'markdown'
  | 'html'
  | 'rawHtml'
  | 'links'
  | 'screenshot'
  | { type: 'json'; schema: any };

interface ScrapeOptions {
  formats?: Format[];
  onlyMainContent?: boolean;
  includeTags?: string[];
  excludeTags?: string[];
  maxAge?: number;
  headers?: Record<string, string>;
  waitFor?: number;
  mobile?: boolean;
  skipTlsVerification?: boolean;
  timeout?: number;
  parsers?: ('pdf')[];
  actions?: Action[];
  location?: LocationConfig;
  removeBase64Images?: boolean;
  blockAds?: boolean;
  proxy?: 'basic' | 'stealth' | 'auto';
  storeInCache?: boolean;
}

interface Action {
  type: 'wait' | 'screenshot' | 'click' | 'write' | 'press' | 'scroll' | 'scrape' | 'execute' | 'pdf';
  milliseconds?: number;
  selector?: string;
  text?: string;
  key?: string;
  direction?: 'up' | 'down';
  script?: string;
}

interface LocationConfig {
  country?: string;
  languages?: string[];
}

interface CrawlOptions {
  scrapeOptions?: ScrapeOptions;
}
```

---

## Implementation Checklist for GraphRAG Backend

### Current Implementation Status

Based on `apps/api/app/services/firecrawl.py`, we currently support:
- ✅ Start crawl (POST /v2/crawl)
- ✅ Get crawl status (GET /v2/crawl/{id})
- ⚠️ Cancel crawl (DELETE /v2/crawl/{id}) - **needs implementation**

### Missing Implementations

#### High Priority

1. **Batch Scrape Operations**
   - [ ] `start_batch_scrape()` - POST /v2/batch/scrape
   - [ ] `get_batch_scrape_status()` - GET /v2/batch/scrape/{id}
   - [ ] `cancel_batch_scrape()` - DELETE /v2/batch/scrape/{id}

2. **Error Handling**
   - [ ] `get_crawl_errors()` - GET /v2/crawl/{id}/errors
   - [ ] `get_batch_scrape_errors()` - GET /v2/batch/scrape/{id}/errors

3. **Crawl Management**
   - [ ] `cancel_crawl()` - DELETE /v2/crawl/{id}

#### Medium Priority

4. **Active Job Monitoring**
   - [ ] `get_active_crawls()` - GET /v2/crawl/active

5. **Params Preview**
   - [ ] `preview_crawl_params()` - POST /v2/crawl/params-preview

#### Low Priority

6. **Pagination Handling**
   - [ ] Helper method for following `next` URLs
   - [ ] Auto-pagination option for SDK methods

### Backend Service Architecture Updates

#### File: `apps/api/app/services/firecrawl.py`

```python
# Add new methods to FirecrawlService class

async def cancel_crawl(self, crawl_id: str) -> dict:
    """Cancel an active crawl job."""

async def start_batch_scrape(
    self,
    urls: list[str],
    webhook_url: str | None = None,
    **options
) -> dict:
    """Start a batch scrape job."""

async def get_batch_scrape_status(self, batch_id: str) -> dict:
    """Get batch scrape status and results."""

async def cancel_batch_scrape(self, batch_id: str) -> dict:
    """Cancel an active batch scrape job."""

async def get_crawl_errors(self, crawl_id: str) -> dict:
    """Get errors for a crawl job."""

async def get_batch_scrape_errors(self, batch_id: str) -> dict:
    """Get errors for a batch scrape job."""

async def get_active_crawls(self) -> dict:
    """List all active crawl jobs."""

async def preview_crawl_params(self, url: str, prompt: str) -> dict:
    """Preview crawl parameters from natural language prompt."""
```

#### New API Endpoints

File: `apps/api/app/api/v1/endpoints/batch_scrape.py` (NEW)

```python
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/batch-scrape")
async def start_batch_scrape(...)

@router.get("/batch-scrape/{batch_id}")
async def get_batch_scrape_status(...)

@router.delete("/batch-scrape/{batch_id}")
async def cancel_batch_scrape(...)

@router.get("/batch-scrape/{batch_id}/errors")
async def get_batch_scrape_errors(...)
```

File: `apps/api/app/api/v1/endpoints/crawl.py` (UPDATES)

```python
# Add new endpoints to existing router

@router.delete("/{crawl_id}")
async def cancel_crawl(...)

@router.get("/{crawl_id}/errors")
async def get_crawl_errors(...)

@router.get("/active")
async def get_active_crawls(...)

@router.post("/params-preview")
async def preview_crawl_params(...)
```

### Frontend Updates

#### New UI Components Needed

1. **Batch Scrape Interface**
   - Multi-URL input (textarea with URL list)
   - Batch progress visualization
   - Per-URL status tracking

2. **Job Management Dashboard**
   - Active jobs list
   - Cancel button for each job
   - Error details modal

3. **Params Preview Tool**
   - Natural language prompt input
   - Preview derived parameters
   - Edit and refine before crawl

---

## Best Practices Summary

### Status Polling

- Poll every **5-10 seconds** for status updates
- Increase interval for long-running jobs (exponential backoff)
- Stop polling when status is `completed` or `failed`
- Always check `expiresAt` - jobs expire after 24 hours

### Error Handling

- Always check errors endpoint after failures
- Implement retry logic for transient errors
- Log `robotsBlocked` URLs separately
- Use `ignoreInvalidURLs: true` for batch scrapes with mixed URL quality

### Pagination

- Always check for `next` field in responses
- Follow pagination links until `next` is null
- Each chunk is max 10MB
- Implement streaming/chunked processing for large crawls

### Webhooks

- Use webhooks instead of polling for real-time updates
- Always verify webhook signatures
- Process webhook payloads asynchronously
- Return 2xx response within 30 seconds

### Job Cancellation

- Cancel jobs before completion to save credits
- Check active crawls periodically to prevent runaway jobs
- Implement automatic cancellation for jobs exceeding time limits

### Params Preview

- Use params preview to validate prompts before crawling
- Helps optimize crawl configuration
- Reduces wasted credits from misconfigured crawls

---

## Additional Resources

- **Firecrawl Documentation:** https://docs.firecrawl.dev
- **API Reference:** https://docs.firecrawl.dev/api-reference/introduction
- **Webhook Guide:** https://docs.firecrawl.dev/webhooks/overview
- **Python SDK:** https://github.com/firecrawl/firecrawl-py
- **Migration Guide (v1→v2):** https://docs.firecrawl.dev/migrate-to-v2

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Firecrawl API Version:** v2
