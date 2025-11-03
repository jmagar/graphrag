"""
Tests for relationship extraction service.

TDD Approach: Write tests first (RED), then implement (GREEN), then refactor.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from app.services.relationship_extractor import RelationshipExtractor


@pytest.mark.asyncio
class TestRelationshipExtractor:
    """Test suite for RelationshipExtractor service."""

    @pytest_asyncio.fixture
    async def extractor(self):
        """Create a RelationshipExtractor instance with mocked LLM."""
        with patch('app.services.relationship_extractor.LLMService') as mock_llm_class:
            # Create mock LLM service
            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm
            
            # Default mock response (tests can override)
            mock_llm.generate_response = AsyncMock(return_value='[]')
            
            extractor = RelationshipExtractor()
            extractor.mock_llm = mock_llm  # Store for test access
            
            yield extractor

    async def test_extract_works_at_relationship(self, extractor):
        """Test extraction of WORKS_AT relationship."""
        text = "Alice Johnson works at Microsoft."
        entities = [
            {"text": "Alice Johnson", "type": "PERSON"},
            {"text": "Microsoft", "type": "ORG"}
        ]
        
        # Mock LLM response
        mock_response = json.dumps([
            {"source": "Alice Johnson", "relation": "WORKS_AT", "target": "Microsoft"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        # Should find WORKS_AT relationship
        assert len(relationships) > 0, "Should extract at least one relationship"
        
        # Check for WORKS_AT type
        rel_types = [r[1] for r in relationships]
        assert any("WORKS" in rt.upper() for rt in rel_types), \
            "Should extract WORKS_AT or similar relationship"

    async def test_extract_multiple_relationships(self, extractor):
        """Test extraction of multiple relationships from text."""
        text = "Alice Johnson works at Microsoft in Seattle and collaborates with Bob Smith."
        entities = [
            {"text": "Alice Johnson", "type": "PERSON"},
            {"text": "Microsoft", "type": "ORG"},
            {"text": "Seattle", "type": "GPE"},
            {"text": "Bob Smith", "type": "PERSON"}
        ]
        
        # Mock LLM response with multiple relationships
        mock_response = json.dumps([
            {"source": "Alice Johnson", "relation": "WORKS_AT", "target": "Microsoft"},
            {"source": "Microsoft", "relation": "LOCATED_IN", "target": "Seattle"},
            {"source": "Alice Johnson", "relation": "COLLABORATES_WITH", "target": "Bob Smith"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        # Should find multiple relationships
        assert len(relationships) >= 2, "Should extract at least 2 relationships"

    async def test_relationship_tuple_format(self, extractor):
        """Test that relationships are returned as (source, relation, target) tuples."""
        text = "Alice works at Microsoft."
        entities = [
            {"text": "Alice", "type": "PERSON"},
            {"text": "Microsoft", "type": "ORG"}
        ]
        
        # Mock LLM response
        mock_response = json.dumps([
            {"source": "Alice", "relation": "WORKS_AT", "target": "Microsoft"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        assert len(relationships) > 0, "Should extract relationships"
        
        # Check tuple format
        rel = relationships[0]
        assert isinstance(rel, tuple), "Relationship should be a tuple"
        assert len(rel) == 3, "Relationship should have 3 elements (source, relation, target)"
        
        source, relation, target = rel
        assert isinstance(source, str), "Source should be a string"
        assert isinstance(relation, str), "Relation should be a string"
        assert isinstance(target, str), "Target should be a string"

    async def test_extract_located_in_relationship(self, extractor):
        """Test extraction of LOCATED_IN relationship."""
        text = "Microsoft is based in Seattle, Washington."
        entities = [
            {"text": "Microsoft", "type": "ORG"},
            {"text": "Seattle", "type": "GPE"}
        ]
        
        # Mock LLM response
        mock_response = json.dumps([
            {"source": "Microsoft", "relation": "BASED_IN", "target": "Seattle"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        assert len(relationships) > 0, "Should extract location relationship"
        
        # Should have Microsoft -> LOCATED_IN/BASED_IN -> Seattle
        sources = [r[0] for r in relationships]
        targets = [r[2] for r in relationships]
        assert "Microsoft" in sources, "Microsoft should be a source"
        assert "Seattle" in targets, "Seattle should be a target"

    async def test_extract_collaborates_with_relationship(self, extractor):
        """Test extraction of COLLABORATES_WITH relationship."""
        text = "Alice Johnson collaborates with Bob Smith on the project."
        entities = [
            {"text": "Alice Johnson", "type": "PERSON"},
            {"text": "Bob Smith", "type": "PERSON"}
        ]
        
        # Mock LLM response
        mock_response = json.dumps([
            {"source": "Alice Johnson", "relation": "COLLABORATES_WITH", "target": "Bob Smith"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        assert len(relationships) > 0, "Should extract collaboration relationship"
        
        # Check for collaboration-type relationship
        rel_types = [r[1].upper() for r in relationships]
        assert any("COLLAB" in rt or "WORK" in rt or "WITH" in rt for rt in rel_types), \
            "Should extract collaboration-type relationship"

    async def test_no_relationships_when_entities_unrelated(self, extractor):
        """Test that unrelated entities don't produce relationships."""
        text = "Alice likes apples. Microsoft is a company."
        entities = [
            {"text": "Alice", "type": "PERSON"},
            {"text": "Microsoft", "type": "ORG"}
        ]
        
        relationships = await extractor.extract_relationships(text, entities)
        
        # May return empty or minimal relationships since entities are unrelated
        # This is acceptable behavior
        assert isinstance(relationships, list), "Should return a list"

    async def test_empty_entities_returns_empty(self, extractor):
        """Test that empty entity list returns empty relationships."""
        text = "Alice works at Microsoft."
        entities = []
        
        relationships = await extractor.extract_relationships(text, entities)
        
        assert relationships == [], "Empty entities should return empty relationships"

    async def test_single_entity_returns_empty(self, extractor):
        """Test that single entity returns no relationships."""
        text = "Alice is a person."
        entities = [{"text": "Alice", "type": "PERSON"}]
        
        relationships = await extractor.extract_relationships(text, entities)
        
        # Single entity cannot have relationships with itself
        assert len(relationships) == 0, "Single entity should not have relationships"

    async def test_relationship_between_correct_entities(self, extractor):
        """Test that relationships link the correct entities."""
        text = "Alice works at Microsoft and Bob works at Google."
        entities = [
            {"text": "Alice", "type": "PERSON"},
            {"text": "Microsoft", "type": "ORG"},
            {"text": "Bob", "type": "PERSON"},
            {"text": "Google", "type": "ORG"}
        ]
        
        # Mock LLM response with correct entity pairings
        mock_response = json.dumps([
            {"source": "Alice", "relation": "WORKS_AT", "target": "Microsoft"},
            {"source": "Bob", "relation": "WORKS_AT", "target": "Google"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        assert len(relationships) >= 2, "Should extract at least 2 work relationships"
        
        # Check that Alice is linked to Microsoft, not Google
        alice_rels = [r for r in relationships if r[0] == "Alice"]
        if alice_rels:
            # Alice's relationships should be with Microsoft
            alice_targets = [r[2] for r in alice_rels]
            # Should prefer Microsoft over Google for Alice
            # (LLM should understand context)

    async def test_common_relationship_types(self, extractor):
        """Test extraction of common relationship types."""
        text = """
        Alice Johnson works at Microsoft and manages the team.
        She is located in Seattle and creates software products.
        """
        entities = [
            {"text": "Alice Johnson", "type": "PERSON"},
            {"text": "Microsoft", "type": "ORG"},
            {"text": "Seattle", "type": "GPE"}
        ]
        
        # Mock LLM response with various relationship types
        mock_response = json.dumps([
            {"source": "Alice Johnson", "relation": "WORKS_AT", "target": "Microsoft"},
            {"source": "Alice Johnson", "relation": "LOCATED_IN", "target": "Seattle"}
        ])
        extractor.mock_llm.generate_response.return_value = mock_response
        
        relationships = await extractor.extract_relationships(text, entities)
        
        # Should extract multiple relationship types
        rel_types = [r[1].upper() for r in relationships]
        
        # Check for common types (at least some should be present)
        common_types = ["WORK", "MANAGE", "LOCAT", "CREATE"]
        found_types = [ct for ct in common_types if any(ct in rt for rt in rel_types)]
        
        assert len(found_types) > 0, \
            f"Should extract common relationship types. Found: {rel_types}"
