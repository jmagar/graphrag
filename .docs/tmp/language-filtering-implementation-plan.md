# Language Filtering Implementation Plan

**Goal**: Filter out non-English content during webhook processing using the same Redis-based pattern

---

## Current Deduplication Pattern (Working)

```python
# webhooks.py - crawl.page handler
if await redis_service.is_page_processed(crawl_id, source_url):
    skipped_count += 1
    continue  # Skip this page
```

---

## Proposed Language Filtering Pattern

### Option 1: Add to Existing Deduplication (Recommended)

**Where**: `apps/api/app/api/v1/endpoints/webhooks.py:94-98`

```python
# In crawl.completed handler
for page_data in data:
    content = page_data.get("markdown", "")
    metadata = page_data.get("metadata", {})
    source_url = metadata.get("sourceURL", "")
    
    # Skip if already processed (deduplication)
    if await redis_service.is_page_processed(crawl_id, source_url):
        skipped_count += 1
        logger.debug(f"Skipping already-processed page: {source_url}")
        continue
    
    # NEW: Detect language and skip if not English
    detected_lang = detect_language(content)
    if detected_lang != "en":
        skipped_count += 1
        logger.info(f"Skipping non-English page ({detected_lang}): {source_url}")
        # Optionally: Mark as processed so we don't check again
        await redis_service.mark_page_processed(crawl_id, source_url)
        continue
    
    # Only English pages reach here
    documents.append({...})
```

---

## Language Detection Options

### Option A: Fast Detection (langdetect)

**Library**: `langdetect` (lightweight, fast)

```python
from langdetect import detect, LangDetectException

def detect_language(text: str) -> str:
    """Detect language of text. Returns 'en' for English, 'unknown' on error."""
    if not text or len(text) < 50:
        return "unknown"
    
    try:
        # Use first 1000 chars for speed
        sample = text[:1000]
        lang = detect(sample)
        return lang
    except LangDetectException:
        return "unknown"
```

**Pros**:
- ✅ Fast (5-10ms per page)
- ✅ Small library (~200KB)
- ✅ Works offline
- ✅ 55 languages supported

**Cons**:
- ⚠️ Not 100% accurate (95%+ for long text)
- ⚠️ Struggles with short text or mixed content

**Add to dependencies**:
```toml
# apps/api/pyproject.toml
dependencies = [
    # ... existing
    "langdetect>=1.0.9",
]
```

---

### Option B: More Accurate (langid or fasttext)

**Library**: `langid` (better accuracy)

```python
import langid

def detect_language(text: str) -> str:
    """Detect language with confidence score."""
    if not text or len(text) < 50:
        return "unknown"
    
    lang, confidence = langid.classify(text)
    
    # Only accept if confidence > 0.9
    if confidence < 0.9:
        return "unknown"
    
    return lang
```

**Pros**:
- ✅ Higher accuracy (97%+)
- ✅ Returns confidence score
- ✅ Works offline

**Cons**:
- ⚠️ Slightly slower (10-20ms)
- ⚠️ Larger model size

---

### Option C: Firecrawl Built-in (If Available)

**Check if Firecrawl already provides language detection**:

```python
# Check metadata from Firecrawl
metadata = page_data.get("metadata", {})
firecrawl_lang = metadata.get("language")  # Might exist!

if firecrawl_lang and firecrawl_lang != "en":
    # Skip - Firecrawl already detected it
    continue
```

**Pros**:
- ✅ Zero latency (already in response)
- ✅ No extra library needed

**Cons**:
- ❌ Only works if Firecrawl provides this field
- ❌ Need to verify if field exists

---

## Implementation Steps

### 1. Add Language Detection Service

**File**: `apps/api/app/services/language_detection.py` (NEW)

```python
"""
Language detection service for filtering non-English content.
"""
import logging
from typing import Optional
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class LanguageDetectionService:
    """Service for detecting language of text content."""
    
    def __init__(self, min_text_length: int = 50):
        """
        Initialize language detection.
        
        Args:
            min_text_length: Minimum text length for detection (default: 50)
        """
        self.min_text_length = min_text_length
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Language code (e.g., 'en', 'es', 'fr') or 'unknown'
        """
        if not text or len(text) < self.min_text_length:
            logger.debug("Text too short for language detection")
            return "unknown"
        
        try:
            # Use first 2000 chars for speed
            sample = text[:2000]
            lang = detect(sample)
            logger.debug(f"Detected language: {lang}")
            return lang
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return "unknown"
    
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
```

---

### 2. Add Configuration

**File**: `apps/api/app/core/config.py`

```python
# Language Filtering
ENABLE_LANGUAGE_FILTERING: bool = True
ALLOWED_LANGUAGES: List[str] = ["en"]  # Only English by default
LANGUAGE_FILTER_MODE: str = "strict"  # "strict" or "lenient"
```

**Modes**:
- `strict`: Only process if detected as English
- `lenient`: Process if English OR unknown (good for short text)

---

### 3. Update Webhook Handler

**File**: `apps/api/app/api/v1/endpoints/webhooks.py`

```python
from app.services.language_detection import LanguageDetectionService

# Initialize service (module level)
lang_service = LanguageDetectionService()

# In crawl.completed handler
elif event_type == "crawl.completed":
    data = payload.get("data", [])
    total_pages = len(data)
    
    documents = []
    skipped_count = 0
    skipped_languages = {}  # Track what languages we're skipping
    
    for page_data in data:
        content = page_data.get("markdown", "")
        metadata = page_data.get("metadata", {})
        source_url = metadata.get("sourceURL", "")
        
        if not content or not source_url:
            continue
        
        # Check deduplication
        if await redis_service.is_page_processed(crawl_id, source_url):
            skipped_count += 1
            logger.debug(f"Skipping already-processed page: {source_url}")
            continue
        
        # NEW: Language filtering
        if settings.ENABLE_LANGUAGE_FILTERING:
            detected_lang = lang_service.detect_language(content)
            
            # Check if language is allowed
            if detected_lang not in settings.ALLOWED_LANGUAGES:
                # Skip non-English
                skipped_count += 1
                skipped_languages[detected_lang] = skipped_languages.get(detected_lang, 0) + 1
                logger.info(f"Skipping {detected_lang} page: {source_url}")
                
                # Mark as processed so we don't check again
                await redis_service.mark_page_processed(crawl_id, source_url)
                continue
        
        # Only English (or allowed language) pages reach here
        documents.append({
            "content": content,
            "source_url": source_url,
            "metadata": metadata,
            "source_type": "crawl"
        })
    
    # Log language filtering stats
    if skipped_languages:
        logger.info(
            f"✓ Crawl {crawl_id}: Filtered out {sum(skipped_languages.values())} "
            f"non-English pages: {skipped_languages}"
        )
```

---

### 4. Add Tests

**File**: `apps/api/tests/services/test_language_detection.py` (NEW)

```python
import pytest
from app.services.language_detection import LanguageDetectionService


class TestLanguageDetection:
    
    @pytest.fixture
    def lang_service(self):
        return LanguageDetectionService()
    
    def test_detect_english(self, lang_service):
        text = "This is a test in English language."
        assert lang_service.detect_language(text) == "en"
    
    def test_detect_spanish(self, lang_service):
        text = "Este es un texto en español para probar la detección."
        assert lang_service.detect_language(text) == "es"
    
    def test_detect_french(self, lang_service):
        text = "Ceci est un texte en français pour tester la détection."
        assert lang_service.detect_language(text) == "fr"
    
    def test_short_text_returns_unknown(self, lang_service):
        text = "Hi"
        assert lang_service.detect_language(text) == "unknown"
    
    def test_is_english(self, lang_service):
        assert lang_service.is_english("This is English text") is True
        assert lang_service.is_english("Este es español") is False
    
    def test_is_english_or_unknown(self, lang_service):
        # English
        assert lang_service.is_english_or_unknown("This is English") is True
        # Short text (unknown)
        assert lang_service.is_english_or_unknown("Hi") is True
        # Spanish
        assert lang_service.is_english_or_unknown("Hola mundo") is False
```

---

## Usage Examples

### Example 1: Crawl with Language Filtering

```bash
# .env
ENABLE_LANGUAGE_FILTERING=true
ALLOWED_LANGUAGES=["en"]
LANGUAGE_FILTER_MODE=strict

# Start crawl
curl -X POST http://localhost:4400/api/v1/crawl \
  -d '{"url": "https://example.com"}'

# Check logs for filtering stats
# Expected:
# ✓ Crawl abc123: Filtered out 23 non-English pages: {'es': 15, 'fr': 5, 'de': 3}
```

### Example 2: Allow Multiple Languages

```bash
# .env
ALLOWED_LANGUAGES=["en", "es", "fr"]

# Will only skip pages in German, Chinese, etc.
```

### Example 3: Disable Language Filtering

```bash
# .env
ENABLE_LANGUAGE_FILTERING=false

# Process all languages (like before)
```

---

## Performance Impact

### Language Detection Speed

**langdetect** (recommended):
- Speed: ~5-10ms per page
- For 100 pages: ~500ms-1s additional processing time

**Mitigation**:
- Only sample first 2000 characters (not entire page)
- Run in same async loop as deduplication check
- Cache language results in Redis if needed

### With Caching

```python
# Optional: Cache detected languages in Redis
async def get_cached_language(self, url: str) -> Optional[str]:
    """Get cached language detection result."""
    key = f"lang:{hashlib.md5(url.encode()).hexdigest()}"
    return await self.redis.get(key)

async def cache_language(self, url: str, lang: str, ttl: int = 86400):
    """Cache language detection result (24hr TTL)."""
    key = f"lang:{hashlib.md5(url.encode()).hexdigest()}"
    await self.redis.set(key, lang, ex=ttl)
```

---

## Benefits

### 1. Cleaner Vector Database
- ✅ Only English content in Qdrant
- ✅ Better search relevance
- ✅ No mixed-language results

### 2. Cost Savings
- ✅ No embeddings generated for non-English pages
- ✅ Reduced storage in Qdrant
- ✅ Faster searches (smaller collection)

### 3. Better User Experience
- ✅ Only relevant language results
- ✅ No confusion from foreign language content
- ✅ Consistent RAG responses

---

## Deployment Plan

### Phase 1: Add Detection Service
1. Add `langdetect` dependency to `pyproject.toml`
2. Create `language_detection.py` service
3. Add unit tests
4. Run `uv sync`

### Phase 2: Add Configuration
1. Add environment variables to `config.py`
2. Update `.env.example`
3. Set `ENABLE_LANGUAGE_FILTERING=true`

### Phase 3: Update Webhook Handler
1. Import LanguageDetectionService
2. Add language check after deduplication
3. Log filtering statistics
4. Test with multi-language crawl

### Phase 4: Monitor
1. Watch logs for language filtering stats
2. Verify only English pages in Qdrant
3. Adjust `LANGUAGE_FILTER_MODE` if needed

---

## Rollback Plan

If language detection causes issues:

```env
# Disable language filtering
ENABLE_LANGUAGE_FILTERING=false

# System continues working as before
```

---

## Alternative: Use Firecrawl's Language Detection

**Check if Firecrawl provides language in metadata**:

```python
# First, inspect a real webhook payload
metadata = page_data.get("metadata", {})
print(f"Firecrawl metadata fields: {metadata.keys()}")

# If 'language' field exists:
if "language" in metadata:
    firecrawl_lang = metadata["language"]
    if firecrawl_lang != "en":
        # Skip - Zero latency!
        continue
```

**Advantage**: No library needed, instant results  
**Check**: Inspect actual Firecrawl webhook to see if field exists

---

## Recommendation

**Implement Option 1 with langdetect**:
1. ✅ Fast enough (5-10ms per page)
2. ✅ Works offline
3. ✅ Easy to implement (same pattern as deduplication)
4. ✅ Configurable (can enable/disable)
5. ✅ Provides filtering statistics

**Expected results** (100 page crawl with 30% non-English):
```
✓ Crawl abc123: 70/100 pages already processed (deduplication)
✓ Crawl abc123: Filtered out 20 non-English pages: {'es': 12, 'fr': 5, 'de': 3}
✓ Crawl abc123: Processing 10 new English pages
```

Total savings: **90% reduction** (100 pages → 10 processed)

---

## Next Steps

1. Add `langdetect` to dependencies
2. Create `LanguageDetectionService`
3. Update webhook handler with language check
4. Add tests
5. Test with multi-language site
6. Monitor and tune

**Estimated implementation time**: 1-2 hours  
**Complexity**: Low (similar to deduplication)  
**Risk**: Low (can disable via config)

