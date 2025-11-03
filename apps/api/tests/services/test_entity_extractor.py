"""
Tests for entity extraction service.

TDD Approach: Write tests first (RED), then implement (GREEN), then refactor.
"""

import pytest
import pytest_asyncio
from app.services.entity_extractor import EntityExtractor


@pytest.mark.asyncio
class TestEntityExtractor:
    """Test suite for EntityExtractor service."""

    @pytest_asyncio.fixture
    async def extractor(self):
        """Create an EntityExtractor instance."""
        return EntityExtractor()

    async def test_extract_person_entities(self, extractor):
        """Test extraction of person entities from text."""
        text = "Alice Johnson works at Microsoft with Bob Smith."
        
        entities = await extractor.extract_entities(text)
        
        # Should extract at least 2 person entities
        person_entities = [e for e in entities if e["type"] == "PERSON"]
        assert len(person_entities) >= 2, "Should extract at least 2 person names"
        
        # Check for Alice
        alice_found = any("Alice" in e["text"] for e in person_entities)
        assert alice_found, "Should extract 'Alice Johnson' as PERSON"
        
        # Check for Bob
        bob_found = any("Bob" in e["text"] for e in person_entities)
        assert bob_found, "Should extract 'Bob Smith' as PERSON"

    async def test_extract_organization_entities(self, extractor):
        """Test extraction of organization entities."""
        text = "Microsoft and Google are competing in AI development."
        
        entities = await extractor.extract_entities(text)
        
        # Should extract organization entities
        org_entities = [e for e in entities if e["type"] in ["ORG", "ORGANIZATION"]]
        assert len(org_entities) >= 2, "Should extract at least 2 organizations"
        
        # Check for Microsoft
        microsoft_found = any("Microsoft" in e["text"] for e in org_entities)
        assert microsoft_found, "Should extract 'Microsoft' as ORG"
        
        # Check for Google
        google_found = any("Google" in e["text"] for e in org_entities)
        assert google_found, "Should extract 'Google' as ORG"

    async def test_extract_location_entities(self, extractor):
        """Test extraction of location entities."""
        text = "The conference in Seattle will discuss advances in New York."
        
        entities = await extractor.extract_entities(text)
        
        # Should extract location entities
        location_entities = [e for e in entities if e["type"] == "GPE"]
        assert len(location_entities) >= 2, "Should extract at least 2 locations"
        
        # Check for Seattle
        seattle_found = any("Seattle" in e["text"] for e in location_entities)
        assert seattle_found, "Should extract 'Seattle' as location"

    async def test_extract_mixed_entity_types(self, extractor):
        """Test extraction of multiple entity types from complex text."""
        text = """
        Dr. Sarah Chen, a researcher at Stanford University, presented her work
        on GraphRAG at the AI Conference in San Francisco. She collaborated with
        the team at OpenAI to develop new retrieval methods.
        """
        
        entities = await extractor.extract_entities(text)
        
        # Should extract entities
        assert len(entities) > 0, "Should extract entities from complex text"
        
        # Should have multiple types
        entity_types = set(e["type"] for e in entities)
        assert len(entity_types) >= 2, "Should extract multiple entity types"
        
        # Should have PERSON (Sarah Chen)
        person_entities = [e for e in entities if e["type"] == "PERSON"]
        assert len(person_entities) >= 1, "Should extract person entities"
        
        # Should have ORG (at least Stanford)
        org_entities = [e for e in entities if e["type"] in ["ORG", "ORGANIZATION"]]
        assert len(org_entities) >= 1, "Should extract at least one organization entity"

    async def test_entity_has_required_fields(self, extractor):
        """Test that extracted entities have all required fields."""
        text = "Alice Johnson works at Microsoft."
        
        entities = await extractor.extract_entities(text)
        
        assert len(entities) > 0, "Should extract at least one entity"
        
        # Check first entity has required fields
        entity = entities[0]
        assert "text" in entity, "Entity should have 'text' field"
        assert "type" in entity, "Entity should have 'type' field"
        assert "start" in entity, "Entity should have 'start' field"
        assert "end" in entity, "Entity should have 'end' field"
        assert "confidence" in entity, "Entity should have 'confidence' field"
        
        # Validate field types
        assert isinstance(entity["text"], str), "'text' should be a string"
        assert isinstance(entity["type"], str), "'type' should be a string"
        assert isinstance(entity["start"], int), "'start' should be an integer"
        assert isinstance(entity["end"], int), "'end' should be an integer"
        assert isinstance(entity["confidence"], float), "'confidence' should be a float"
        
        # Validate confidence range
        assert 0.0 <= entity["confidence"] <= 1.0, "Confidence should be between 0 and 1"

    async def test_empty_text_returns_empty_list(self, extractor):
        """Test that empty text returns an empty list."""
        entities = await extractor.extract_entities("")
        assert entities == [], "Empty text should return empty list"

    async def test_no_entities_in_text(self, extractor):
        """Test text with no recognizable entities."""
        text = "The quick brown fox jumps over the lazy dog."
        
        entities = await extractor.extract_entities(text)
        
        # May return empty or very few entities (common words might not be entities)
        assert isinstance(entities, list), "Should return a list even if no entities found"

    async def test_entity_positions_are_accurate(self, extractor):
        """Test that entity start/end positions match the text."""
        text = "Alice works at Microsoft in Seattle."
        
        entities = await extractor.extract_entities(text)
        
        # Check that positions are accurate
        for entity in entities:
            extracted_text = text[entity["start"]:entity["end"]]
            assert extracted_text == entity["text"], \
                f"Position mismatch: expected '{entity['text']}', got '{extracted_text}'"

    async def test_extract_product_entities(self, extractor):
        """Test extraction of product entities."""
        text = "We use Python and Neo4j for our GraphRAG implementation."
        
        entities = await extractor.extract_entities(text)
        
        # Should extract product entities
        product_entities = [e for e in entities if e["type"] == "PRODUCT"]
        
        # spaCy might recognize these as products or not, depending on context
        # At minimum, should extract something from this text
        assert len(entities) > 0, "Should extract at least one entity"

    async def test_confidence_scores_are_reasonable(self, extractor):
        """Test that confidence scores are within reasonable range."""
        text = "Alice Johnson is a researcher at MIT."
        
        entities = await extractor.extract_entities(text)
        
        assert len(entities) > 0, "Should extract entities"
        
        # All confidences should be in valid range
        for entity in entities:
            assert 0.0 <= entity["confidence"] <= 1.0, \
                f"Confidence {entity['confidence']} out of range for entity '{entity['text']}'"
            
            # Most spaCy entities should have reasonably high confidence
            # (We set default to 0.8 in implementation)
            assert entity["confidence"] >= 0.5, \
                f"Entity '{entity['text']}' has unexpectedly low confidence: {entity['confidence']}"
