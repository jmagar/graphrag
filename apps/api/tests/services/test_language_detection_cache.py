"""
Tests for language detection caching functionality.

Tests that language detection results are cached to avoid redundant processing.
"""

import time
from app.services.language_detection import LanguageDetectionService


class TestLanguageDetectionCache:
    """Test suite for language detection caching."""

    def test_language_detection_caches_results(self):
        """
        Test that same text is detected only once, subsequent calls use cache.
        
        RED: This test will FAIL initially (no caching implemented).
        """
        service = LanguageDetectionService()
        
        text = "This is a sample English text that should be cached for performance."
        
        # First call - should detect and cache
        result1 = service.detect_language(text)
        
        # Second call - should use cache
        result2 = service.detect_language(text)
        
        # Results should be the same
        assert result1 == result2
        assert result1 == "en"
        
        # Check cache stats
        stats = service.get_cache_stats()
        assert stats["hits"] >= 1  # At least one cache hit
        assert stats["cache_size"] >= 1  # At least one entry cached

    def test_cache_handles_different_content(self):
        """
        Test that different content generates different cache keys.
        
        RED: This test will FAIL initially (no cache key generation).
        """
        service = LanguageDetectionService()
        
        text1 = "This is English text about technology and science."
        text2 = "Este es un texto en español sobre tecnología y ciencia."
        
        # Detect both
        lang1 = service.detect_language(text1)
        lang2 = service.detect_language(text2)
        
        # Should detect different languages
        assert lang1 == "en"
        assert lang2 == "es"
        
        # Both should be cached separately
        stats = service.get_cache_stats()
        assert stats["cache_size"] == 2  # Two different entries

    def test_cache_respects_size_limit(self):
        """
        Test that cache evicts oldest entries when limit reached.
        
        RED: This test will FAIL initially (no size limit enforcement).
        """
        # Create service (will use default cache size from settings)
        service = LanguageDetectionService()
        
        # Get cache max size
        stats_initial = service.get_cache_stats()
        max_size = stats_initial["cache_maxsize"]
        
        # Add more entries than cache size
        for i in range(max_size + 10):
            text = f"This is sample English text number {i} with unique content."
            service.detect_language(text)
        
        # Cache should not exceed max size
        stats = service.get_cache_stats()
        assert stats["cache_size"] <= max_size

    def test_cache_stats_tracking(self):
        """
        Test that cache hits and misses are tracked correctly.
        
        RED: This test will FAIL initially (no stats tracking).
        """
        service = LanguageDetectionService()
        
        text = "This is sample text for cache statistics testing. It needs to be longer than 50 characters."
        
        # First call - should be a miss
        service.detect_language(text)
        stats_after_first = service.get_cache_stats()
        assert stats_after_first["misses"] == 1
        assert stats_after_first["hits"] == 0
        
        # Second call - should be a hit
        service.detect_language(text)
        stats_after_second = service.get_cache_stats()
        assert stats_after_second["hits"] == 1
        assert stats_after_second["misses"] == 1
        
        # Hit rate should be 50%
        assert stats_after_second["hit_rate_percent"] == 50.0

    def test_clear_cache_resets_state(self):
        """
        Test that clear_cache() removes all entries and resets stats.
        
        RED: This test will FAIL initially (no clear_cache method).
        """
        service = LanguageDetectionService()
        
        # Add some entries (make them longer than min_text_length)
        text1 = "This is English text that is long enough to be detected properly by the language detection service."
        text2 = "This is more English text that is also sufficiently long for proper language detection to work."
        
        service.detect_language(text1)
        service.detect_language(text2)
        service.detect_language(text1)  # Cache hit
        
        # Verify cache has entries
        stats_before = service.get_cache_stats()
        assert stats_before["cache_size"] > 0
        assert stats_before["hits"] > 0
        
        # Clear cache
        service.clear_cache()
        
        # Stats should be reset
        stats_after = service.get_cache_stats()
        assert stats_after["cache_size"] == 0
        assert stats_after["hits"] == 0
        assert stats_after["misses"] == 0

    def test_cache_performance_improvement(self):
        """
        Test that cached calls are significantly faster than uncached.
        
        RED: This test will FAIL initially (no caching = no speedup).
        """
        service = LanguageDetectionService()
        
        text = "This is a longer sample text for performance testing. " * 20
        
        # First call - uncached (slower)
        start_uncached = time.perf_counter()
        result1 = service.detect_language(text)
        time_uncached = time.perf_counter() - start_uncached
        
        # Second call - cached (faster)
        start_cached = time.perf_counter()
        result2 = service.detect_language(text)
        time_cached = time.perf_counter() - start_cached
        
        # Results should match
        assert result1 == result2
        
        # Cached call should be at least 10x faster
        # (langdetect takes ~10-50ms, cache lookup ~0.1ms)
        assert time_cached < time_uncached / 10

    def test_cache_key_stability(self):
        """
        Test that same text produces same cache key consistently.
        
        RED: This test will FAIL initially (no cache key generation).
        """
        service = LanguageDetectionService()
        
        text = "This is consistent text for cache key testing."
        
        # Generate cache keys multiple times
        key1 = service._generate_cache_key(text)
        key2 = service._generate_cache_key(text)
        key3 = service._generate_cache_key(text)
        
        # All keys should be identical
        assert key1 == key2 == key3
        
        # Key should be a valid MD5 hex digest (32 chars)
        assert len(key1) == 32
        assert all(c in "0123456789abcdef" for c in key1)
