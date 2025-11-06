"""
Application configuration using Pydantic settings.
"""

import re
import logging
from typing import List, Dict, Any
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Supported language codes (ISO 639-1)
SUPPORTED_LANGUAGES = [
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "ja",
    "zh",
    "ko",
    "ar",
    "hi",
    "nl",
    "pl",
    "tr",
    "vi",
    "th",
    "sv",
    "no",
    "da",
]


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "GraphRAG API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:4300",
        "http://localhost:4301",
    ]
    CORS_EXTRA_ORIGINS: str = ""  # Additional origins (comma-separated)

    # Firecrawl v2 API
    FIRECRAWL_URL: str
    FIRECRAWL_API_KEY: str
    FIRECRAWL_WEBHOOK_SECRET: str = ""  # Optional: for webhook signature verification

    # Qdrant vector database
    QDRANT_URL: str
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "graphrag"

    # TEI embeddings service
    TEI_URL: str

    # Reranker service (optional)
    RERANKER_URL: str = ""

    # Ollama for LLM (optional)
    OLLAMA_URL: str = ""
    OLLAMA_MODEL: str = "qwen3:4b"

    # Webhook URL for Firecrawl callbacks
    WEBHOOK_BASE_URL: str = "http://localhost:4400"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 4202  # Redis container exposed on port 4202
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./graphrag.db"

    # Neo4j Graph Database
    NEO4J_URI: str = "bolt://localhost:7688"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str  # Required - no default for security

    # Feature Flags
    ENABLE_STREAMING_PROCESSING: bool = True
    ENABLE_LANGUAGE_FILTERING: bool = False  # Disabled by default for safety
    ENABLE_QUERY_CACHE: bool = True  # Enable Redis query result caching
    ENABLE_CIRCUIT_BREAKER_PERSISTENCE: bool = False  # Enable Redis-backed circuit breaker state persistence
    DEBUG: bool = False

    # Language Filtering
    ALLOWED_LANGUAGES: str = "en"  # Comma-separated language codes (e.g., "en" or "en,es,fr")
    LANGUAGE_FILTER_MODE: str = "lenient"  # "strict" or "lenient" (allow unknown)

    # Language Detection Caching
    LANGUAGE_DETECTION_CACHE_SIZE: int = 1000  # Maximum cached detection results
    LANGUAGE_DETECTION_SAMPLE_SIZE: int = 2000  # Characters to sample for detection

    # Query Cache Configuration
    QUERY_CACHE_TTL: int = 300  # Default cache TTL in seconds (5 minutes)

    # Validators
    @field_validator("REDIS_PORT")
    @classmethod
    def validate_redis_port(cls, v: int) -> int:
        """Validate Redis port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Invalid Redis port: {v}. Must be between 1 and 65535.")
        return v

    @field_validator("ALLOWED_LANGUAGES")
    @classmethod
    def validate_allowed_languages(cls, v: str) -> str:
        """Validate language codes are supported."""
        if not v:
            return v

        codes = [lang.strip().lower() for lang in v.split(",")]
        invalid_codes = [code for code in codes if code and code not in SUPPORTED_LANGUAGES]

        if invalid_codes:
            raise ValueError(
                f"Unsupported language codes: {invalid_codes}. "
                f"Supported codes: {SUPPORTED_LANGUAGES}"
            )

        # Return normalized (lowercase, no extra spaces)
        return ",".join(codes)

    @field_validator("LANGUAGE_FILTER_MODE")
    @classmethod
    def validate_language_filter_mode(cls, v: str) -> str:
        """Validate language filter mode."""
        v = v.lower()
        if v not in ("strict", "lenient"):
            raise ValueError(f"Invalid language filter mode: {v}. Must be 'strict' or 'lenient'.")
        return v

    @field_validator("WEBHOOK_BASE_URL")
    @classmethod
    def validate_webhook_base_url(cls, v: str) -> str:
        """Validate webhook base URL format."""
        if not re.match(r"^https?://", v):
            raise ValueError(f"Invalid webhook URL: {v}. Must start with http:// or https://")

        # Warn about localhost in production (will be checked in model_validator)
        if "localhost" in v or "127.0.0.1" in v:
            logger.warning(
                "⚠️ Webhook URL uses localhost. This won't work if Firecrawl "
                "is on a different host. Consider using a public URL or container name."
            )

        return v.rstrip("/")  # Remove trailing slash

    @model_validator(mode="after")
    def validate_feature_flags(self) -> "Settings":
        """Cross-field validation for feature flags."""
        # If language filtering is enabled, ensure languages are configured
        if self.ENABLE_LANGUAGE_FILTERING and not self.ALLOWED_LANGUAGES:
            raise ValueError(
                "ENABLE_LANGUAGE_FILTERING is true but ALLOWED_LANGUAGES is empty. "
                "Specify at least one language code or disable the feature."
            )

        # Log feature flag configuration
        if self.ENABLE_STREAMING_PROCESSING and self.ENABLE_LANGUAGE_FILTERING:
            logger.info(
                "ℹ️ Both streaming and language filtering enabled. "
                "Pages will be filtered before processing."
            )

        # Add extra CORS origins if provided
        if self.CORS_EXTRA_ORIGINS:
            extra_origins = [origin.strip() for origin in self.CORS_EXTRA_ORIGINS.split(",") if origin.strip()]
            self.CORS_ORIGINS.extend(extra_origins)
            logger.info(f"✅ Added {len(extra_origins)} extra CORS origins")

        return self

    # Properties
    @property
    def allowed_languages_list(self) -> list[str]:
        """Parse ALLOWED_LANGUAGES string into a list."""
        return [lang.strip() for lang in self.ALLOWED_LANGUAGES.split(",") if lang.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode (not DEBUG)."""
        return not self.DEBUG

    def validate_webhook_config(self) -> None:
        """
        Validate webhook configuration for production.

        Raises:
            ValueError: If webhook secret is not set in production mode
        """
        if self.is_production and not self.FIRECRAWL_WEBHOOK_SECRET:
            raise ValueError(
                "FIRECRAWL_WEBHOOK_SECRET is required in production mode. "
                "Set DEBUG=true to allow insecure webhooks in development."
            )

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get sanitized configuration summary for logging.

        Returns:
            Dictionary with config values, sensitive data masked
        """
        return {
            "debug": self.DEBUG,
            "redis": {
                "host": self.REDIS_HOST,
                "port": self.REDIS_PORT,
                "db": self.REDIS_DB,
                "password_set": bool(self.REDIS_PASSWORD),
            },
            "features": {
                "streaming_processing": self.ENABLE_STREAMING_PROCESSING,
                "language_filtering": self.ENABLE_LANGUAGE_FILTERING,
                "query_cache": self.ENABLE_QUERY_CACHE,
                "circuit_breaker_persistence": self.ENABLE_CIRCUIT_BREAKER_PERSISTENCE,
            },
            "language": {
                "allowed": self.allowed_languages_list if self.ENABLE_LANGUAGE_FILTERING else None,
                "mode": self.LANGUAGE_FILTER_MODE if self.ENABLE_LANGUAGE_FILTERING else None,
            },
            "services": {
                "firecrawl_url": self.FIRECRAWL_URL,
                "firecrawl_key_set": bool(self.FIRECRAWL_API_KEY),
                "webhook_secret_set": bool(self.FIRECRAWL_WEBHOOK_SECRET),
                "qdrant_url": self.QDRANT_URL,
                "tei_url": self.TEI_URL,
                "ollama_url": self.OLLAMA_URL,
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validate_webhook_config()


settings = Settings()
