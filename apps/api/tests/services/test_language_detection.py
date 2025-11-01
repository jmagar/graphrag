"""
Tests for language detection service.
"""

import pytest
from app.services.language_detection import LanguageDetectionService


class TestLanguageDetection:
    """Test suite for LanguageDetectionService."""

    @pytest.fixture
    def lang_service(self):
        """Fixture providing LanguageDetectionService instance."""
        return LanguageDetectionService()

    def test_detect_english(self, lang_service):
        """Test detection of English text."""
        text = "This is a test in English language. We need enough text for accurate detection."
        assert lang_service.detect_language(text) == "en"

    def test_detect_spanish(self, lang_service):
        """Test detection of Spanish text."""
        text = "Este es un texto en español para probar la detección de idioma. Necesitamos texto suficiente."
        assert lang_service.detect_language(text) == "es"

    def test_detect_french(self, lang_service):
        """Test detection of French text."""
        text = "Ceci est un texte en français pour tester la détection de langue. Il faut du texte suffisant."
        assert lang_service.detect_language(text) == "fr"

    def test_detect_german(self, lang_service):
        """Test detection of German text."""
        text = "Dies ist ein Text auf Deutsch zum Testen der Spracherkennung. Wir brauchen genug Text."
        assert lang_service.detect_language(text) == "de"

    def test_short_text_returns_unknown(self, lang_service):
        """Test that short text returns unknown."""
        text = "Hi"
        assert lang_service.detect_language(text) == "unknown"

    def test_empty_text_returns_unknown(self, lang_service):
        """Test that empty text returns unknown."""
        assert lang_service.detect_language("") == "unknown"
        assert lang_service.detect_language(None) == "unknown"

    def test_is_english(self, lang_service):
        """Test is_english method."""
        english_text = "This is definitely English text with enough content for detection."
        spanish_text = "Este es definitivamente texto en español con suficiente contenido para la detección."
        
        assert lang_service.is_english(english_text) is True
        assert lang_service.is_english(spanish_text) is False

    def test_is_english_or_unknown(self, lang_service):
        """Test is_english_or_unknown method."""
        # English
        english_text = "This is English text with enough content."
        assert lang_service.is_english_or_unknown(english_text) is True
        
        # Short text (unknown)
        assert lang_service.is_english_or_unknown("Hi") is True
        
        # Spanish
        spanish_text = "Esto es texto en español con suficiente contenido."
        assert lang_service.is_english_or_unknown(spanish_text) is False

    def test_is_allowed_language(self, lang_service):
        """Test is_allowed_language method."""
        english_text = "This is English text with enough content for detection."
        spanish_text = "Este es texto en español con suficiente contenido para la detección."
        
        # English allowed
        assert lang_service.is_allowed_language(english_text, ["en"]) is True
        assert lang_service.is_allowed_language(spanish_text, ["en"]) is False
        
        # Multiple languages allowed
        assert lang_service.is_allowed_language(english_text, ["en", "es"]) is True
        assert lang_service.is_allowed_language(spanish_text, ["en", "es"]) is True
        
        # Unknown is always allowed
        assert lang_service.is_allowed_language("Hi", ["en"]) is True

    def test_custom_min_length(self):
        """Test custom minimum text length."""
        service = LanguageDetectionService(min_text_length=100)
        short_text = "This is a short text."
        assert service.detect_language(short_text) == "unknown"
