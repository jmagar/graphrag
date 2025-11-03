"""
Entity extraction service using spaCy NER.

Extracts named entities (people, organizations, locations, etc.) from text.
"""

import logging
from typing import List, Dict, Any
import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)


# Supported entity types for extraction
ENTITY_TYPES = [
    "PERSON",  # People (Alice Johnson, Dr. Smith)
    "ORG",  # Organizations (Microsoft, MIT)
    "GPE",  # Geopolitical entities (Seattle, USA)
    "LOCATION",  # Non-GPE locations (Office 405, Building A)
    "LOC",  # Locations (alternate spaCy label)
    "PRODUCT",  # Products, tools (Python, Neo4j)
    "EVENT",  # Events (Conference 2023, Launch)
    "WORK_OF_ART",  # Documents, papers, books
    "DATE",  # Temporal entities
    "NORP",  # Nationalities or religious or political groups
    "FAC",  # Buildings, airports, highways, bridges, etc.
]


class EntityExtractor:
    """Extract entities from text using spaCy NER."""

    def __init__(self):
        """Initialize the entity extractor with spaCy model."""
        try:
            # Load large English model for best accuracy
            self.nlp: Language = spacy.load("en_core_web_lg")
            logger.info("✅ Loaded spaCy model 'en_core_web_lg' for entity extraction")
        except OSError as e:
            logger.error(
                f"❌ Failed to load spaCy model 'en_core_web_lg'. "
                f"Run: python -m spacy download en_core_web_lg. Error: {e}"
            )
            raise

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using spaCy NER.

        Args:
            text: The text to extract entities from

        Returns:
            List of entity dictionaries with fields:
            - text: Entity text
            - type: Entity type (PERSON, ORG, GPE, etc.)
            - start: Character start position
            - end: Character end position
            - confidence: Confidence score (0-1)

        Example:
            >>> extractor = EntityExtractor()
            >>> entities = await extractor.extract_entities("Alice works at Microsoft.")
            >>> entities
            [
                {
                    "text": "Alice",
                    "type": "PERSON",
                    "start": 0,
                    "end": 5,
                    "confidence": 0.8
                },
                {
                    "text": "Microsoft",
                    "type": "ORG",
                    "start": 15,
                    "end": 24,
                    "confidence": 0.8
                }
            ]
        """
        if not text or not text.strip():
            return []

        # Process text with spaCy
        doc = self.nlp(text)

        # Extract entities
        entities = []
        for ent in doc.ents:
            # Filter to supported entity types
            if ent.label_ not in ENTITY_TYPES:
                continue

            entity = {
                "text": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": 0.8,  # Default confidence for spaCy entities
            }
            entities.append(entity)

        logger.debug(
            f"Extracted {len(entities)} entities from text "
            f"({len(text)} chars): {[e['text'] for e in entities]}"
        )

        return entities

    async def extract_entities_with_validation(
        self, text: str, min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Extract entities with confidence filtering.

        Args:
            text: The text to extract entities from
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of high-confidence entities
        """
        entities = await self.extract_entities(text)

        # Filter by confidence
        filtered_entities = [e for e in entities if e["confidence"] >= min_confidence]

        logger.debug(
            f"Filtered {len(entities)} entities to {len(filtered_entities)} "
            f"with min_confidence={min_confidence}"
        )

        return filtered_entities

    def get_entity_types(self) -> List[str]:
        """
        Get list of supported entity types.

        Returns:
            List of entity type labels
        """
        return ENTITY_TYPES.copy()
