"""
Language detection service for filtering non-English content.
"""

import hashlib
import logging
from functools import lru_cache
from typing import Dict
from langdetect import detect, LangDetectException
from app.core.config import settings

logger = logging.getLogger(__name__)


class LanguageDetectionService:
    """
    Service for detecting language of text content with caching.
    
    Caches detection results based on content hash to avoid redundant
    processing of identical or similar content.
    """

    def __init__(self, min_text_length: int = 50):
        """
        Initialize language detection.

        Args:
            min_text_length: Minimum text length for detection (default: 50)
        """
        self.min_text_length = min_text_length
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Create instance-level cached function
        @lru_cache(maxsize=settings.LANGUAGE_DETECTION_CACHE_SIZE)
        def _cached_detect(cache_key: str, text_sample: str) -> str:
            """Internal cached language detection."""
            try:
                lang = detect(text_sample)
                logger.debug(f"Detected language: {lang} (cache_key: {cache_key[:8]}...)")
                return lang
            except LangDetectException as e:
                logger.warning(f"Language detection failed: {e}")
                return "unknown"
        
        self._detect_language_impl = _cached_detect

    def _generate_cache_key(self, text: str) -> str:
        """
        Generate cache key from text content.
        
        Args:
            text: Text to hash
            
        Returns:
            MD5 hex digest of text sample
        """
        sample = text[:settings.LANGUAGE_DETECTION_SAMPLE_SIZE]
        return hashlib.md5(sample.encode('utf-8', errors='ignore')).hexdigest()

    def detect_language(self, text: str) -> str:
        """
        Detect language of text with caching.

        Args:
            text: Text content to analyze

        Returns:
            Language code (e.g., 'en', 'es', 'fr') or 'unknown'
        """
        if not text or len(text) < self.min_text_length:
            logger.debug("Text too short for language detection")
            return "unknown"

        # Generate cache key
        sample = text[:settings.LANGUAGE_DETECTION_SAMPLE_SIZE]
        cache_key = self._generate_cache_key(text)
        
        # Check cache info before call
        cache_info_before = self._detect_language_impl.cache_info()
        
        # Call cached implementation
        result = self._detect_language_impl(cache_key, sample)
        
        # Track statistics
        cache_info_after = self._detect_language_impl.cache_info()
        if cache_info_after.hits > cache_info_before.hits:
            self._cache_hits += 1
            logger.debug(f"Cache hit for language detection: {result}")
        else:
            self._cache_misses += 1
        
        return result
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hits, misses, size, and hit_rate
        """
        cache_info = self._detect_language_impl.cache_info()
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "cache_size": cache_info.currsize,
            "cache_maxsize": cache_info.maxsize,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    def clear_cache(self) -> None:
        """Clear the language detection cache."""
        self._detect_language_impl.cache_clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Language detection cache cleared")

    def is_english(self, text: str) -> bool:
        """
        Check if text is in English.

        Args:
            text: Text content to check

        Returns:
            True if English, False otherwise
        """
        lang = self.detect_language(text)
        return lang == "en"

    def is_english_or_unknown(self, text: str) -> bool:
        """
        Check if text is English or language couldn't be detected.

        Useful for being lenient with short text.

        Args:
            text: Text content to check

        Returns:
            True if English or unknown, False if detected as other language
        """
        lang = self.detect_language(text)
        return lang in ("en", "unknown")

    def is_allowed_language(self, text: str, allowed_languages: list[str]) -> bool:
        """
        Check if text is in one of the allowed languages.

        Args:
            text: Text content to check
            allowed_languages: List of allowed language codes (e.g., ['en', 'es'])

        Returns:
            True if language is allowed or unknown, False otherwise
        """
        lang = self.detect_language(text)
        return lang in allowed_languages or lang == "unknown"
