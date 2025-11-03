"""
Comprehensive tests for app/dependencies.py dependency injection functions.

Tests verify the singleton pattern implementation for all 6 services.
"""

import pytest
from unittest.mock import MagicMock

from app.dependencies import (
    get_firecrawl_service, set_firecrawl_service, clear_firecrawl_service,
    get_vector_db_service, set_vector_db_service, clear_vector_db_service,
    get_embeddings_service, set_embeddings_service, clear_embeddings_service,
    get_llm_service, set_llm_service, clear_llm_service,
    get_redis_service, set_redis_service, clear_redis_service,
    get_language_detection_service, set_language_detection_service, clear_language_detection_service,
    clear_all_services,
)
from app.services.firecrawl import FirecrawlService
from app.services.vector_db import VectorDBService
from app.services.embeddings import EmbeddingsService
from app.services.llm import LLMService
from app.services.redis_service import RedisService
from app.services.language_detection import LanguageDetectionService


@pytest.fixture(autouse=True)
def reset_all_services():
    """Automatically reset all services before and after each test."""
    clear_all_services()
    yield
    clear_all_services()


class TestFirecrawlServiceDependency:
    """Tests for FirecrawlService dependency injection functions."""

    def test_get_without_set_raises_runtime_error(self):
        """Test that get_firecrawl_service raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_firecrawl_service()
        assert "FirecrawlService not initialized" in str(exc_info.value)

    def test_set_and_get_returns_same_instance(self):
        """Test that set/get returns the same instance."""
        mock = MagicMock(spec=FirecrawlService)
        set_firecrawl_service(mock)
        assert get_firecrawl_service() is mock

    def test_clear_resets_to_none(self):
        """Test that clear resets the service."""
        set_firecrawl_service(MagicMock(spec=FirecrawlService))
        clear_firecrawl_service()
        with pytest.raises(RuntimeError):
            get_firecrawl_service()

    def test_set_twice_overwrites(self):
        """Test that calling set twice overwrites."""
        mock1 = MagicMock(spec=FirecrawlService)
        mock2 = MagicMock(spec=FirecrawlService)
        set_firecrawl_service(mock1)
        set_firecrawl_service(mock2)
        assert get_firecrawl_service() is mock2


class TestVectorDBServiceDependency:
    """Tests for VectorDBService dependency injection functions."""

    def test_get_without_set_raises_runtime_error(self):
        """Test that get_vector_db_service raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_vector_db_service()
        assert "VectorDBService not initialized" in str(exc_info.value)

    def test_set_and_get_returns_same_instance(self):
        """Test that set/get returns the same instance."""
        mock = MagicMock(spec=VectorDBService)
        set_vector_db_service(mock)
        assert get_vector_db_service() is mock

    def test_clear_resets_to_none(self):
        """Test that clear resets the service."""
        set_vector_db_service(MagicMock(spec=VectorDBService))
        clear_vector_db_service()
        with pytest.raises(RuntimeError):
            get_vector_db_service()

    def test_set_twice_overwrites(self):
        """Test that calling set twice overwrites."""
        mock1 = MagicMock(spec=VectorDBService)
        mock2 = MagicMock(spec=VectorDBService)
        set_vector_db_service(mock1)
        set_vector_db_service(mock2)
        assert get_vector_db_service() is mock2


class TestEmbeddingsServiceDependency:
    """Tests for EmbeddingsService dependency injection functions."""

    def test_get_without_set_raises_runtime_error(self):
        """Test that get_embeddings_service raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_embeddings_service()
        assert "EmbeddingsService not initialized" in str(exc_info.value)

    def test_set_and_get_returns_same_instance(self):
        """Test that set/get returns the same instance."""
        mock = MagicMock(spec=EmbeddingsService)
        set_embeddings_service(mock)
        assert get_embeddings_service() is mock

    def test_clear_resets_to_none(self):
        """Test that clear resets the service."""
        set_embeddings_service(MagicMock(spec=EmbeddingsService))
        clear_embeddings_service()
        with pytest.raises(RuntimeError):
            get_embeddings_service()

    def test_set_twice_overwrites(self):
        """Test that calling set twice overwrites."""
        mock1 = MagicMock(spec=EmbeddingsService)
        mock2 = MagicMock(spec=EmbeddingsService)
        set_embeddings_service(mock1)
        set_embeddings_service(mock2)
        assert get_embeddings_service() is mock2


class TestLLMServiceDependency:
    """Tests for LLMService dependency injection functions."""

    def test_get_without_set_raises_runtime_error(self):
        """Test that get_llm_service raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_llm_service()
        assert "LLMService not initialized" in str(exc_info.value)

    def test_set_and_get_returns_same_instance(self):
        """Test that set/get returns the same instance."""
        mock = MagicMock(spec=LLMService)
        set_llm_service(mock)
        assert get_llm_service() is mock

    def test_clear_resets_to_none(self):
        """Test that clear resets the service."""
        set_llm_service(MagicMock(spec=LLMService))
        clear_llm_service()
        with pytest.raises(RuntimeError):
            get_llm_service()

    def test_set_twice_overwrites(self):
        """Test that calling set twice overwrites."""
        mock1 = MagicMock(spec=LLMService)
        mock2 = MagicMock(spec=LLMService)
        set_llm_service(mock1)
        set_llm_service(mock2)
        assert get_llm_service() is mock2


class TestRedisServiceDependency:
    """Tests for RedisService dependency injection functions."""

    def test_get_without_set_raises_runtime_error(self):
        """Test that get_redis_service raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_redis_service()
        assert "RedisService not initialized" in str(exc_info.value)

    def test_set_and_get_returns_same_instance(self):
        """Test that set/get returns the same instance."""
        mock = MagicMock(spec=RedisService)
        set_redis_service(mock)
        assert get_redis_service() is mock

    def test_clear_resets_to_none(self):
        """Test that clear resets the service."""
        set_redis_service(MagicMock(spec=RedisService))
        clear_redis_service()
        with pytest.raises(RuntimeError):
            get_redis_service()

    def test_set_twice_overwrites(self):
        """Test that calling set twice overwrites."""
        mock1 = MagicMock(spec=RedisService)
        mock2 = MagicMock(spec=RedisService)
        set_redis_service(mock1)
        set_redis_service(mock2)
        assert get_redis_service() is mock2


class TestLanguageDetectionServiceDependency:
    """Tests for LanguageDetectionService dependency injection functions."""

    def test_get_without_set_raises_runtime_error(self):
        """Test that get_language_detection_service raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_language_detection_service()
        assert "LanguageDetectionService not initialized" in str(exc_info.value)

    def test_set_and_get_returns_same_instance(self):
        """Test that set/get returns the same instance."""
        mock = MagicMock(spec=LanguageDetectionService)
        set_language_detection_service(mock)
        assert get_language_detection_service() is mock

    def test_clear_resets_to_none(self):
        """Test that clear resets the service."""
        set_language_detection_service(MagicMock(spec=LanguageDetectionService))
        clear_language_detection_service()
        with pytest.raises(RuntimeError):
            get_language_detection_service()

    def test_set_twice_overwrites(self):
        """Test that calling set twice overwrites."""
        mock1 = MagicMock(spec=LanguageDetectionService)
        mock2 = MagicMock(spec=LanguageDetectionService)
        set_language_detection_service(mock1)
        set_language_detection_service(mock2)
        assert get_language_detection_service() is mock2


class TestClearAllServices:
    """Tests for clear_all_services() utility function."""

    def test_clear_all_services_clears_all_six_services(self):
        """Test that clear_all_services clears all 6 service singletons."""
        set_firecrawl_service(MagicMock(spec=FirecrawlService))
        set_vector_db_service(MagicMock(spec=VectorDBService))
        set_embeddings_service(MagicMock(spec=EmbeddingsService))
        set_llm_service(MagicMock(spec=LLMService))
        set_redis_service(MagicMock(spec=RedisService))
        set_language_detection_service(MagicMock(spec=LanguageDetectionService))

        clear_all_services()

        with pytest.raises(RuntimeError):
            get_firecrawl_service()
        with pytest.raises(RuntimeError):
            get_vector_db_service()
        with pytest.raises(RuntimeError):
            get_embeddings_service()
        with pytest.raises(RuntimeError):
            get_llm_service()
        with pytest.raises(RuntimeError):
            get_redis_service()
        with pytest.raises(RuntimeError):
            get_language_detection_service()

    def test_clear_all_is_idempotent(self):
        """Test that calling clear_all_services multiple times is safe."""
        clear_all_services()
        clear_all_services()  # Should not raise
        with pytest.raises(RuntimeError):
            get_firecrawl_service()
