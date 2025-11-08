# GraphRAG Codebase Remediation Plan

**Date Created:** 2025-11-08
**Audit Report:** Based on comprehensive codebase review (118 issues identified)
**Priority:** CRITICAL - Address before production deployment
**Estimated Timeline:** 4-6 weeks (with 2-3 developers)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 1: Security & Production Blockers (1-2 weeks)](#phase-1-security--production-blockers)
3. [Phase 2: Reliability & Performance (2-3 weeks)](#phase-2-reliability--performance)
4. [Phase 3: Code Quality & Architecture (1-2 weeks)](#phase-3-code-quality--architecture)
5. [Testing Strategy](#testing-strategy)
6. [Deployment Checklist](#deployment-checklist)

---

## Executive Summary

The GraphRAG codebase audit identified **118 issues** across security, performance, code quality, and deployment readiness:

- **26 CRITICAL** - Must fix before production
- **37 HIGH** - Should fix for production stability
- **33 MEDIUM** - Quality improvements
- **22 LOW** - Nice to have

**Current Status:** ⚠️ NOT PRODUCTION-READY

**Primary Concerns:**
1. No authentication/authorization
2. Resource leaks in core services
3. Hardcoded credentials
4. Missing production deployment configuration
5. No error recovery mechanisms

---

## Phase 1: Security & Production Blockers (1-2 weeks)

### 1.1 Implement Authentication System ⚠️ CRITICAL

**Issue:** All API endpoints are publicly accessible without authentication.

**Solution:** Implement API key authentication with optional JWT for user sessions.

#### Step 1: Add Authentication Dependencies

```bash
cd apps/api
uv add pyjwt[crypto] passlib[bcrypt]
```

#### Step 2: Create Authentication Service

**File:** `apps/api/app/services/auth.py`

```python
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 60 * 24  # 24 hours

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)
```

#### Step 3: Add API Key Middleware

**File:** `apps/api/app/middleware/auth.py`

```python
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.config import settings
from app.services.auth import AuthService

security = HTTPBearer()

auth_service = AuthService(secret_key=settings.SECRET_KEY)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verify API key or JWT token.

    Supports two authentication methods:
    1. Static API key (for service-to-service)
    2. JWT token (for user sessions)
    """
    token = credentials.credentials

    # Check if it's a static API key
    if token in settings.API_KEYS:
        return {"type": "api_key", "key": token}

    # Check if it's a JWT token
    payload = auth_service.verify_token(token)
    if payload:
        return {"type": "jwt", "user_id": payload.get("sub"), "email": payload.get("email")}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def verify_admin(credentials: dict = Security(verify_api_key)) -> dict:
    """Verify admin-level access for sensitive operations."""
    if credentials["type"] == "api_key":
        # API keys have full access
        return credentials

    # For JWT tokens, check admin role
    # This requires user management system (future work)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )
```

#### Step 4: Update Configuration

**File:** `apps/api/app/core/config.py`

```python
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # ... existing config ...

    # Authentication
    SECRET_KEY: str = Field(..., description="JWT secret key - MUST be set in production")
    API_KEYS: List[str] = Field(default_factory=list, description="Comma-separated API keys")

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if v == "changeme" or v.startswith("your_"):
            raise ValueError("SECRET_KEY must be changed from default/placeholder")
        return v

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v):
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v
```

#### Step 5: Protect Endpoints

**File:** `apps/api/app/api/v1/endpoints/crawl.py`

```python
from fastapi import Depends
from app.middleware.auth import verify_api_key

@router.post("/", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),
    credentials: dict = Depends(verify_api_key),  # ADD THIS
):
    """Start a new crawl - requires authentication."""
    # ... existing code ...
```

**Protect all endpoints similarly:**
- Public: `/health`, `/docs`
- Authenticated: All `/api/v1/*` endpoints
- Admin only: `/api/v1/cache/invalidate/*`

#### Step 6: Add Environment Variables

**File:** `.env.example`

```bash
# Authentication
SECRET_KEY=your_secret_key_at_least_32_characters_long
API_KEYS=key1,key2,key3
```

**Generate secret key:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### 1.2 Remove Hardcoded Credentials ⚠️ CRITICAL

**Issue:** Production config contains hardcoded test credentials and internal hostnames.

**Solution:** Remove all defaults, require environment variables.

**File:** `apps/api/app/core/config.py`

```python
# BEFORE (INSECURE)
REDIS_HOST: str = "steamy-wsl"  # ❌ Machine-specific
REDIS_PORT: int = 4202
NEO4J_PASSWORD: str = "testpassword123"  # ❌ Test password

# AFTER (SECURE)
REDIS_HOST: str = Field(..., description="Redis hostname")
REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
NEO4J_PASSWORD: str = Field(..., description="Neo4j password - REQUIRED")

@field_validator("NEO4J_PASSWORD")
@classmethod
def validate_neo4j_password(cls, v: str) -> str:
    if not v:
        raise ValueError("NEO4J_PASSWORD is required")
    if v == "testpassword123" or len(v) < 8:
        raise ValueError("NEO4J_PASSWORD must be secure (8+ characters, not test password)")
    return v

@field_validator("REDIS_HOST")
@classmethod
def validate_redis_host(cls, v: str) -> str:
    if not v:
        raise ValueError("REDIS_HOST is required")
    # Don't allow machine-specific hostnames
    if v in ["steamy-wsl", "localhost"] and not settings.DEBUG:
        raise ValueError("Use proper hostname in production, not localhost/machine-specific")
    return v
```

**Update `.env.example`:**

```bash
# Redis Configuration
REDIS_HOST=redis  # Use service name in Docker, or actual hostname
REDIS_PORT=6379
REDIS_PASSWORD=  # Leave empty for no auth, or set strong password

# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=  # REQUIRED: Set strong password (8+ chars)
```

---

### 1.3 Fix Resource Leaks - Connection Pooling ⚠️ CRITICAL

**Issue:** `EmbeddingsService` and `LLMService` create new HTTP client per request.

**Impact:** 10-100x performance degradation, file descriptor exhaustion.

#### Fix EmbeddingsService

**File:** `apps/api/app/services/embeddings.py`

```python
import httpx
from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbeddingsService:
    def __init__(self):
        self.base_url = settings.TEI_URL

        # CREATE PERSISTENT CLIENT WITH CONNECTION POOLING
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create persistent HTTP client with connection pooling."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:  # Double-check locking
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(60.0, connect=10.0),
                        limits=httpx.Limits(
                            max_connections=50,
                            max_keepalive_connections=20,
                        ),
                    )
                    logger.info(f"✅ Created persistent HTTP client for TEI at {self.base_url}")
        return self._client

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using TEI service."""
        if not texts:
            return []

        client = await self._get_client()

        response = await client.post(
            f"{self.base_url}/embed",
            json={"inputs": texts},
            timeout=60.0,
        )
        response.raise_for_status()
        result: List[List[float]] = response.json()
        return result

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("✅ EmbeddingsService HTTP client closed")
```

#### Fix LLMService

**File:** `apps/api/app/services/llm.py`

```python
class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

        # CREATE PERSISTENT CLIENT
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create persistent HTTP client with connection pooling."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(120.0, connect=10.0),
                        limits=httpx.Limits(
                            max_connections=20,
                            max_keepalive_connections=10,
                        ),
                    )
                    logger.info(f"✅ Created persistent HTTP client for Ollama at {self.base_url}")
        return self._client

    async def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate LLM response using Ollama."""
        if not self.base_url:
            raise HTTPException(
                status_code=503,
                detail="LLM service not configured"
            )

        client = await self._get_client()

        # Build prompt
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_message = f"Context:\n{context}\n\nQuestion: {query}"
        messages.append({"role": "user", "content": user_message})

        # Call Ollama API
        response = await client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()

        result = response.json()
        return result["message"]["content"]

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("✅ LLMService HTTP client closed")
```

#### Update Lifespan Shutdown

**File:** `apps/api/app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... startup code ...

    yield

    # Shutdown - close all services
    logger.info("🔄 Shutting down services...")

    services_to_close = [
        ("FirecrawlService", firecrawl_service),
        ("VectorDBService", vector_db_service),
        ("EmbeddingsService", embeddings_service),  # ADD THIS
        ("LLMService", llm_service),  # ADD THIS
    ]

    for service_name, service in services_to_close:
        try:
            if hasattr(service, 'close'):
                await asyncio.wait_for(service.close(), timeout=5.0)
                logger.info(f"✅ {service_name} closed")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ {service_name} shutdown timed out")
        except Exception as e:
            logger.error(f"❌ Error closing {service_name}: {e}")
```

---

### 1.4 Fix Cypher Injection Risk ⚠️ CRITICAL

**Issue:** GraphDB relationship type uses f-string formatting without validation.

**File:** `apps/api/app/services/graph_db.py`

```python
# BEFORE (VULNERABLE)
query = f"""
MATCH (a:Entity {{id: $source_id}})
MATCH (b:Entity {{id: $target_id}})
MERGE (a)-[r:{relationship_type}]->(b)  # ❌ Direct interpolation
...
"""

# AFTER (SECURE)
from typing import Literal

# Define allowed relationship types
RELATIONSHIP_TYPES = {
    "MENTIONS",
    "RELATED_TO",
    "EXTRACTED_FROM",
    "PART_OF",
    "REFERENCES",
}

RelationshipType = Literal["MENTIONS", "RELATED_TO", "EXTRACTED_FROM", "PART_OF", "REFERENCES"]

async def create_relationship(
    self,
    source_id: str,
    target_id: str,
    relationship_type: RelationshipType,  # Use Literal type
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a relationship between two entities."""

    # VALIDATE BEFORE QUERY CONSTRUCTION
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(
            f"Invalid relationship type: {relationship_type}. "
            f"Must be one of: {', '.join(sorted(RELATIONSHIP_TYPES))}"
        )

    # Now safe to use in query
    query = f"""
    MATCH (a:Entity {{id: $source_id}})
    MATCH (b:Entity {{id: $target_id}})
    MERGE (a)-[r:{relationship_type}]->(b)
    SET r.metadata = $metadata_json,
        r.created_at = datetime()
    RETURN r
    """

    # ... rest of code ...
```

---

### 1.5 Fix Duplicate Python Dependencies ⚠️ CRITICAL

**Issue:** `pyproject.toml` has two dev dependency sections with conflicting versions.

**File:** `apps/api/pyproject.toml`

```toml
# REMOVE THIS SECTION (Lines 26-36)
# [project.optional-dependencies]
# dev = [
#     "pytest>=8.3.0",
#     ...
# ]

# KEEP ONLY THIS SECTION (consolidate all deps)
[dependency-groups]
dev = [
    "anyio>=4.11.0",
    "black>=24.10.0",
    "fakeredis>=2.32.0",      # Use higher version
    "mypy>=1.13.0",
    "pytest>=8.4.2",          # Use higher version
    "pytest-asyncio>=1.2.0",  # Use higher version
    "pytest-cov>=7.0.0",      # Use higher version
    "respx>=0.22.0",          # Use higher version
    "ruff>=0.7.0",
]
```

**After editing, run:**

```bash
cd apps/api
uv sync --dev
uv lock
```

---

### 1.6 Create Production Docker Configuration ⚠️ CRITICAL

**Issue:** No Docker deployment configuration exists.

#### Backend Dockerfile

**File:** `apps/api/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:4400/health')" || exit 1

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4400", "--workers", "4"]
```

#### Frontend Dockerfile

**File:** `apps/web/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./
RUN npm ci --production=false

FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build application
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 4300

ENV PORT 4300
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

#### Docker Compose for Development

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    ports:
      - "4400:4400"
    environment:
      - DEBUG=false
      - FIRECRAWL_URL=${FIRECRAWL_URL}
      - FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY}
      - QDRANT_URL=http://qdrant:6333
      - TEI_URL=http://tei:8080
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OLLAMA_URL=http://ollama:11434
      - SECRET_KEY=${SECRET_KEY}
      - API_KEYS=${API_KEYS}
    depends_on:
      - redis
      - qdrant
      - neo4j
    restart: unless-stopped

  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    ports:
      - "4300:4300"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:4400
    depends_on:
      - api
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    restart: unless-stopped

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j-data:/data
    restart: unless-stopped

  tei:
    image: ghcr.io/huggingface/text-embeddings-inference:latest
    ports:
      - "8080:8080"
    environment:
      - MODEL_ID=BAAI/bge-small-en-v1.5
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped

volumes:
  redis-data:
  qdrant-data:
  neo4j-data:
  ollama-data:
```

#### Update Next.js Config for Docker

**File:** `apps/web/next.config.ts`

```typescript
const nextConfig: NextConfig = {
  output: 'standalone',  // ADD THIS for Docker
  compress: true,
  poweredByHeader: false,

  // ... rest of config
};
```

---

### 1.7 Add CSRF Protection ⚠️ CRITICAL

**Issue:** State-changing endpoints lack CSRF protection.

**Install dependency:**

```bash
cd apps/api
uv add fastapi-csrf-protect
```

**File:** `apps/api/app/middleware/csrf.py`

```python
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = settings.SECRET_KEY
    cookie_name: str = "csrftoken"
    cookie_samesite: str = "lax"
    cookie_secure: bool = not settings.DEBUG
    cookie_httponly: bool = True

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()
```

**File:** `apps/api/app/main.py`

```python
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

# Add to main.py
@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": "CSRF validation failed"}
    )

# Add CSRF token endpoint
@app.get("/api/v1/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    response = JSONResponse(content={"detail": "CSRF cookie set"})
    csrf_protect.set_csrf_cookie(response)
    return response
```

**Protect endpoints:**

```python
@router.post("/", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    csrf_protect: CsrfProtect = Depends(),  # ADD THIS
    credentials: dict = Depends(verify_api_key),
):
    await csrf_protect.validate_csrf(request)  # ADD THIS
    # ... rest of code
```

---

## Phase 2: Reliability & Performance (2-3 weeks)

### 2.1 Add Retry Logic with Exponential Backoff

**Install dependency:**

```bash
cd apps/api
uv add tenacity
```

**File:** `apps/api/app/services/embeddings.py`

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

class EmbeddingsService:
    # ... existing code ...

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with automatic retry on transient failures."""
        if not texts:
            return []

        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.base_url}/embed",
                json={"inputs": texts},
                timeout=60.0,
            )
            response.raise_for_status()
            result: List[List[float]] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            # Don't retry client errors (4xx)
            if 400 <= e.response.status_code < 500:
                raise
            # Retry server errors (5xx)
            logger.warning(f"TEI service error (will retry): {e}")
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"TEI network error (will retry): {e}")
            raise
```

**Apply same pattern to:**
- `VectorDBService` (Qdrant operations)
- `LLMService` (Ollama calls)
- `GraphDBService` (Neo4j queries)

---

### 2.2 Implement Circuit Breakers

**File:** `apps/api/app/core/circuit_breaker.py`

```python
from circuitbreaker import circuit
from typing import Callable, Any

def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
):
    """
    Decorator to add circuit breaker to async functions.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying again
        expected_exception: Exception type to catch
    """
    return circuit(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )
```

**Usage in services:**

```python
from app.core.circuit_breaker import with_circuit_breaker

class EmbeddingsService:
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=60)
    @retry(...)
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        # ... existing code ...
```

---

### 2.3 Add Rate Limiting

**Install dependency:**

```bash
cd apps/api
uv add slowapi
```

**File:** `apps/api/app/middleware/rate_limit.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail)
        }
    )
```

**File:** `apps/api/app/main.py`

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
```

**Apply to endpoints:**

```python
from app.middleware.rate_limit import limiter

@router.post("/", response_model=CrawlResponse)
@limiter.limit("10/minute")  # 10 crawls per minute per IP
async def start_crawl(
    request: Request,  # Required for rate limiting
    crawl_request: CrawlRequest,
    # ... other dependencies
):
    # ... code ...
```

**Recommended limits:**
- `/api/v1/crawl`: 10/minute
- `/api/v1/query`: 20/minute
- `/api/v1/chat`: 30/minute
- `/api/v1/cache/invalidate/*`: 1/minute (admin only)

---

### 2.4 Fix Cache Invalidation Strategy

**File:** `apps/api/app/services/vector_db.py`

```python
async def upsert_document(
    self,
    doc_id: str,
    content: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    invalidate_cache: bool = False,  # CHANGE DEFAULT TO FALSE
) -> None:
    """Upsert a document to the vector database."""
    # ... existing upsert code ...

    # Only invalidate cache if explicitly requested
    # OR use selective invalidation (future: track which queries touched this doc)
    if invalidate_cache and self.query_cache:
        # Selective invalidation: only invalidate queries that might have returned this doc
        # For now, we skip invalidation and rely on TTL
        pass
        # await self.query_cache.invalidate_collection(self.collection_name)  # Remove this
```

**Alternative: Increase Cache TTL**

**File:** `apps/api/app/core/config.py`

```python
# Increase from 300s (5 min) to 3600s (1 hour)
QUERY_CACHE_TTL: int = Field(default=3600, description="Query cache TTL in seconds")
```

---

### 2.5 Add Error Boundaries (Frontend)

**File:** `apps/web/app/error.tsx`

```typescript
'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log error to monitoring service (Sentry, etc.)
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="max-w-md text-center">
        <h1 className="text-4xl font-bold text-red-600 mb-4">
          Something went wrong
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {error.message || 'An unexpected error occurred'}
        </p>
        <Button onClick={reset}>
          Try again
        </Button>
      </div>
    </div>
  )
}
```

**File:** `apps/web/app/global-error.tsx`

```typescript
'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-4">Fatal Error</h2>
            <p className="mb-4">{error.message}</p>
            <button onClick={reset}>Try again</button>
          </div>
        </div>
      </body>
    </html>
  )
}
```

---

### 2.6 Replace alert() with Toast Notifications

**File:** `apps/web/components/layout/LeftSidebar.tsx`

```typescript
// BEFORE
const handleAddSource = () => {
  alert('Add Source functionality - to be implemented');
};

// AFTER
import { toast } from 'sonner';

const handleAddSource = () => {
  toast.info('Add Source feature coming soon!', {
    duration: 3000,
  });
};
```

**Apply to all files:**
- `components/layout/LeftSidebar.tsx`
- `components/chat/ChatHeader.tsx`

---

### 2.7 Add Production Logging Configuration

**File:** `apps/api/app/core/logging.py`

```python
import logging
import logging.config
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(log_level: str = "INFO", json_logs: bool = True):
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to use JSON format (True for production)
    """

    if json_logs:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            }
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logging.root.handlers = []
    logging.root.addHandler(handler)
    logging.root.setLevel(log_level)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

**File:** `apps/api/app/main.py`

```python
from app.core.logging import setup_logging

# Setup logging before anything else
setup_logging(
    log_level=settings.LOG_LEVEL,
    json_logs=not settings.DEBUG
)
```

**Add to config:**

```python
LOG_LEVEL: str = Field(default="INFO", description="Logging level")
```

---

## Phase 3: Code Quality & Architecture (1-2 weeks)

### 3.1 Consolidate Dependency Injection

**Issue:** graph.py, scrape.py, extract.py define their own DI functions.

**Solution:** Move all service getters to `dependencies.py`.

**File:** `apps/api/app/dependencies.py`

```python
# Add these to centralized dependencies

_hybrid_query_engine: Optional[HybridQueryEngine] = None
_graph_db_service: Optional[GraphDBService] = None

def get_hybrid_query_engine() -> HybridQueryEngine:
    """Get the global HybridQueryEngine instance."""
    if _hybrid_query_engine is None:
        raise RuntimeError("HybridQueryEngine not initialized. Call set_hybrid_query_engine() first.")
    return _hybrid_query_engine

def set_hybrid_query_engine(engine: HybridQueryEngine) -> None:
    """Set the global HybridQueryEngine instance."""
    global _hybrid_query_engine
    _hybrid_query_engine = engine

def get_graph_db_service() -> GraphDBService:
    """Get the global GraphDBService instance."""
    if _graph_db_service is None:
        raise RuntimeError("GraphDBService not initialized. Call set_graph_db_service() first.")
    return _graph_db_service

def set_graph_db_service(service: GraphDBService) -> None:
    """Set the global GraphDBService instance."""
    global _graph_db_service
    _graph_db_service = service
```

**File:** `apps/api/app/api/v1/endpoints/graph.py`

```python
# REMOVE lines 29-57 (duplicate DI code)

# REPLACE with import
from app.dependencies import get_hybrid_query_engine, get_graph_db_service

@router.post("/knowledge-graph/query", response_model=HybridQueryResponse)
async def hybrid_query(
    request: HybridQueryRequest,
    hybrid_engine: HybridQueryEngine = Depends(get_hybrid_query_engine),  # Use central DI
):
    # ... code ...
```

**File:** `apps/api/app/api/v1/endpoints/scrape.py` and `extract.py`

```python
# REMOVE local get_firecrawl_service() definitions (lines 21-23)

# REPLACE with import
from app.dependencies import get_firecrawl_service

@router.post("/", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    firecrawl_service: FirecrawlService = Depends(get_firecrawl_service),  # Use central DI
):
    # ... code ...
```

---

### 3.2 Centralize Frontend Configuration

**File:** `apps/web/lib/config.ts`

```typescript
/**
 * Centralized configuration for the frontend application.
 * All environment variables and constants should be defined here.
 */

// Validate required environment variables
const requiredEnvVars = ['NEXT_PUBLIC_API_URL'] as const;

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Required environment variable ${envVar} is not set`);
  }
}

export const API_CONFIG = {
  /**
   * Backend API base URL
   */
  BACKEND_URL: process.env.NEXT_PUBLIC_API_URL!,

  /**
   * Request timeouts (milliseconds)
   */
  TIMEOUTS: {
    DEFAULT: 30000,      // 30 seconds
    SCRAPE: 60000,       // 60 seconds
    EXTRACT: 90000,      // 90 seconds
    STREAM: 120000,      // 120 seconds
    HEALTH_CHECK: 5000,  // 5 seconds
  },

  /**
   * Retry configuration
   */
  RETRY: {
    MAX_ATTEMPTS: 3,
    INITIAL_DELAY: 1000,  // 1 second
    MAX_DELAY: 10000,     // 10 seconds
    BACKOFF_FACTOR: 2,
  },
} as const;

export const APP_CONFIG = {
  /**
   * Application metadata
   */
  NAME: 'GraphRAG',
  VERSION: '1.0.0',

  /**
   * Feature flags
   */
  FEATURES: {
    ENABLE_STREAMING: true,
    ENABLE_FILE_UPLOAD: false,
    ENABLE_DARK_MODE: true,
  },
} as const;

// Type exports for TypeScript
export type ApiConfig = typeof API_CONFIG;
export type AppConfig = typeof APP_CONFIG;
```

**Update all API routes to use config:**

```typescript
// BEFORE
const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4400';

// AFTER
import { API_CONFIG } from '@/lib/config';

const backendUrl = API_CONFIG.BACKEND_URL;
const timeout = API_CONFIG.TIMEOUTS.DEFAULT;
```

---

### 3.3 Generate Shared Types from Pydantic Models

**Install tool:**

```bash
cd apps/api
uv add --dev pydantic2ts
```

**File:** `apps/api/scripts/generate_types.py`

```python
#!/usr/bin/env python
"""Generate TypeScript types from Pydantic models."""

import json
from pathlib import Path
from pydantic2ts import generate_typescript_defs

# Import all Pydantic models
from app.api.v1.endpoints.crawl import CrawlRequest, CrawlResponse, CrawlStatusResponse
from app.api.v1.endpoints.query import QueryRequest, QueryResponse, SearchResult
from app.api.v1.endpoints.conversations import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

# Models to export
models = [
    CrawlRequest,
    CrawlResponse,
    CrawlStatusResponse,
    QueryRequest,
    QueryResponse,
    SearchResult,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
]

# Output file
output_file = Path(__file__).parent.parent.parent / "web" / "types" / "api.ts"
output_file.parent.mkdir(exist_ok=True)

# Generate TypeScript
generate_typescript_defs(
    module="app.api.v1.endpoints",
    output=output_file,
    json2ts_cmd="npx json2ts"
)

print(f"✅ Generated TypeScript types: {output_file}")
```

**Add to package.json:**

```json
{
  "scripts": {
    "generate:types": "cd ../api && uv run python scripts/generate_types.py"
  }
}
```

---

### 3.4 Add Missing Tests

#### Backend: Query Endpoint Tests

**File:** `apps/api/tests/api/v1/endpoints/test_query.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_query_with_rag(test_client: AsyncClient, mock_embeddings_service, mock_vector_db_service, mock_llm_service):
    """Test RAG query flow: query → embedding → vector search → LLM response."""

    # Mock embedding generation
    mock_embeddings_service.generate_embedding.return_value = [0.1] * 1024

    # Mock vector search results
    mock_vector_db_service.search.return_value = [
        {
            "id": "doc_1",
            "score": 0.95,
            "content": "GraphRAG is a retrieval-augmented generation system.",
            "metadata": {"sourceURL": "https://example.com/docs"}
        }
    ]

    # Mock LLM response
    mock_llm_service.generate_response.return_value = "GraphRAG combines web crawling with vector search and LLMs."

    # Make request
    response = await test_client.post(
        "/api/v1/query",
        json={
            "query": "What is GraphRAG?",
            "use_llm": True,
            "limit": 5
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert "llm_response" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "doc_1"
    assert "GraphRAG combines" in data["llm_response"]

@pytest.mark.anyio
async def test_query_without_llm(test_client: AsyncClient, mock_embeddings_service, mock_vector_db_service):
    """Test vector search only (no LLM)."""

    mock_embeddings_service.generate_embedding.return_value = [0.1] * 1024
    mock_vector_db_service.search.return_value = []

    response = await test_client.post(
        "/api/v1/query",
        json={
            "query": "Test query",
            "use_llm": False,
            "limit": 10
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert "llm_response" not in data or data["llm_response"] is None
```

#### Frontend: ChatInput Tests

**File:** `apps/web/__tests__/components/input/ChatInput.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatInput from '@/components/input/ChatInput';

describe('ChatInput', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders input field and send button', () => {
    render(<ChatInput onSubmit={mockOnSubmit} />);

    expect(screen.getByPlaceholderText(/type a message/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('submits message on Enter key', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/type a message/i);
    await user.type(input, 'Hello world{Enter}');

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith('Hello world');
    });
  });

  it('creates new line on Shift+Enter', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/type a message/i);
    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2');

    expect(input).toHaveValue('Line 1\nLine 2');
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('disables input while loading', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={true} />);

    const input = screen.getByPlaceholderText(/type a message/i);
    const button = screen.getByRole('button', { name: /send/i });

    expect(input).toBeDisabled();
    expect(button).toBeDisabled();
  });
});
```

---

## Testing Strategy

### Unit Tests
- All service classes (100% coverage target)
- All API endpoints (100% coverage target)
- All React components (80% coverage target)

### Integration Tests
- E2E RAG flow: crawl → embed → query → response
- Webhook processing: Firecrawl → backend → vector DB
- Authentication flow: login → protected endpoint access

### Performance Tests
- Concurrent crawl handling (10+ simultaneous)
- Query cache performance (1000+ queries/second)
- Connection pool exhaustion scenarios

### Security Tests
- Authentication bypass attempts
- CSRF token validation
- SQL/Cypher injection attempts
- XSS prevention
- Rate limiting enforcement

---

## Deployment Checklist

### Pre-Deployment

- [ ] All CRITICAL issues resolved
- [ ] Authentication implemented and tested
- [ ] Connection pooling verified (no resource leaks)
- [ ] Environment variables documented in `.env.example`
- [ ] Docker images build successfully
- [ ] Database migrations tested
- [ ] Secrets rotated (no test/default values)
- [ ] HTTPS/TLS configured
- [ ] CORS origins restricted to production domains
- [ ] Rate limiting configured
- [ ] Logging configured (JSON format, appropriate levels)
- [ ] Monitoring/alerting configured (Sentry, Prometheus, etc.)
- [ ] Backup strategy documented and tested
- [ ] Health checks verified
- [ ] Load testing completed (target: 1000 concurrent users)

### Deployment

- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] Verify all external services reachable (Firecrawl, Qdrant, etc.)
- [ ] Test authentication flow
- [ ] Test crawl → query flow
- [ ] Monitor error rates for 24 hours
- [ ] Deploy to production with blue-green or canary strategy
- [ ] Monitor metrics (CPU, memory, request latency, error rate)
- [ ] Verify health check endpoints responding
- [ ] Test production authentication
- [ ] Enable monitoring alerts

### Post-Deployment

- [ ] Monitor error rates (target: <1%)
- [ ] Monitor response times (target: p95 <500ms for queries)
- [ ] Verify cache hit rates (target: >50%)
- [ ] Check database connection pools (no exhaustion)
- [ ] Review logs for errors/warnings
- [ ] Verify backup jobs running
- [ ] Test disaster recovery procedures
- [ ] Document any deployment issues
- [ ] Update runbook with production specifics

---

## Environment Variables Reference

### Required (Production)

```bash
# Authentication
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
API_KEYS=key1,key2,key3

# External Services
FIRECRAWL_URL=https://api.firecrawl.dev
FIRECRAWL_API_KEY=<your_api_key>
FIRECRAWL_WEBHOOK_SECRET=<webhook_secret>

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=<strong_password>
NEO4J_URI=bolt://neo4j.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<strong_password>

# Vector/AI Services
QDRANT_URL=https://qdrant.example.com
TEI_URL=https://tei.example.com
OLLAMA_URL=https://ollama.example.com
OLLAMA_MODEL=qwen3:4b

# Configuration
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://app.example.com,https://www.example.com
WEBHOOK_BASE_URL=https://api.example.com
```

### Optional

```bash
# Features
ENABLE_QUERY_CACHE=true
ENABLE_LANGUAGE_FILTERING=false
ENABLE_CIRCUIT_BREAKER_PERSISTENCE=true

# Monitoring
SENTRY_DSN=<sentry_dsn>
PROMETHEUS_ENABLED=true

# Cache
QUERY_CACHE_TTL=3600
LANGUAGE_DETECTION_CACHE_SIZE=1000
```

---

## Timeline Estimate

### Phase 1: Security & Production Blockers (1-2 weeks)
- **Week 1:**
  - Day 1-2: Authentication system (1.1)
  - Day 3: Remove hardcoded credentials (1.2)
  - Day 4-5: Fix resource leaks (1.3)

- **Week 2:**
  - Day 1: Fix Cypher injection (1.4)
  - Day 2: Fix duplicate dependencies (1.5)
  - Day 3-5: Docker configuration (1.6)

### Phase 2: Reliability & Performance (2-3 weeks)
- **Week 3:**
  - Day 1-2: Retry logic (2.1)
  - Day 3: Circuit breakers (2.2)
  - Day 4: Rate limiting (2.3)
  - Day 5: Cache strategy (2.4)

- **Week 4:**
  - Day 1-2: Error boundaries (2.5)
  - Day 3: Toast notifications (2.6)
  - Day 4-5: Production logging (2.7)

### Phase 3: Code Quality & Architecture (1-2 weeks)
- **Week 5:**
  - Day 1-2: Consolidate DI (3.1)
  - Day 3: Centralize config (3.2)
  - Day 4-5: Generate shared types (3.3)

- **Week 6:**
  - Day 1-3: Add missing tests (3.4)
  - Day 4-5: Integration testing and deployment prep

---

## Success Metrics

### Performance
- Query latency p95: <500ms
- Crawl throughput: 100+ pages/minute
- Cache hit rate: >50%
- API uptime: >99.9%

### Quality
- Test coverage: >80% (backend), >70% (frontend)
- Zero critical/high vulnerabilities
- Code quality score: A (SonarQube)

### Operational
- Mean time to recovery (MTTR): <15 minutes
- Error rate: <1%
- Successful deployments: >95%

---

## Support & Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Tools
- Backend: pytest, mypy, ruff, black
- Frontend: Jest, ESLint, Prettier
- Monitoring: Sentry, Prometheus, Grafana
- CI/CD: GitHub Actions

### Team Responsibilities
- **Backend Lead:** Phase 1.1-1.5, Phase 2.1-2.3
- **DevOps Lead:** Phase 1.6-1.7, Deployment
- **Frontend Lead:** Phase 2.5-2.6, Frontend tests
- **QA Lead:** Testing strategy, integration tests

---

**Last Updated:** 2025-11-08
**Next Review:** After Phase 1 completion
