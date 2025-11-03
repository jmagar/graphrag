"""
Tests for Neo4j graph database service.

TDD Approach: Write tests first (RED), then implement (GREEN), then refactor.
"""

import pytest
import pytest_asyncio
from app.services.graph_db import GraphDBService


@pytest.mark.asyncio
class TestGraphDBService:
    """Test suite for GraphDBService."""

    @pytest_asyncio.fixture
    async def graph_db(self):
        """Create a GraphDBService instance and clean up after tests."""
        service = GraphDBService()
        await service.initialize()
        
        yield service
        
        # Cleanup: Delete test data
        async with service.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        
        await service.close()

    async def test_initialize_and_close(self):
        """Test service initialization and cleanup."""
        service = GraphDBService()
        await service.initialize()
        
        # Should be able to run a simple query
        async with service.driver.session() as session:
            result = await session.run("RETURN 1 as num")
            record = await result.single()
            assert record["num"] == 1
        
        await service.close()

    async def test_create_entity(self, graph_db):
        """Test creating an entity node in the graph."""
        entity_id = "test_entity_1"
        entity_type = "PERSON"
        text = "Alice Johnson"
        metadata = {"confidence": 0.9, "source": "test"}
        
        result = await graph_db.create_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            text=text,
            metadata=metadata
        )
        
        # Verify entity was created
        assert result is not None
        
        # Query to verify
        async with graph_db.driver.session() as session:
            query_result = await session.run(
                "MATCH (e:Entity {id: $entity_id}) RETURN e",
                entity_id=entity_id
            )
            record = await query_result.single()
            assert record is not None
            
            entity = record["e"]
            assert entity["id"] == entity_id
            assert entity["type"] == entity_type
            assert entity["text"] == text

    async def test_create_duplicate_entity_merges(self, graph_db):
        """Test that creating duplicate entities merges (MERGE semantics)."""
        entity_id = "test_entity_2"
        
        # Create first time
        await graph_db.create_entity(
            entity_id=entity_id,
            entity_type="PERSON",
            text="Bob Smith",
            metadata={}
        )
        
        # Create again with different text
        await graph_db.create_entity(
            entity_id=entity_id,
            entity_type="PERSON",
            text="Bob Smith Updated",
            metadata={"updated": True}
        )
        
        # Should only have one entity (MERGE behavior)
        async with graph_db.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {id: $entity_id}) RETURN count(e) as count",
                entity_id=entity_id
            )
            record = await result.single()
            assert record["count"] == 1

    async def test_create_relationship(self, graph_db):
        """Test creating a relationship between two entities."""
        # Create source entity
        source_id = "entity_a"
        await graph_db.create_entity(
            entity_id=source_id,
            entity_type="PERSON",
            text="Alice",
            metadata={}
        )
        
        # Create target entity
        target_id = "entity_b"
        await graph_db.create_entity(
            entity_id=target_id,
            entity_type="ORG",
            text="Microsoft",
            metadata={}
        )
        
        # Create relationship
        rel_result = await graph_db.create_relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type="WORKS_AT",
            metadata={"since": 2020}
        )
        
        assert rel_result is not None
        
        # Verify relationship exists
        async with graph_db.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Entity {id: $source_id})-[r:WORKS_AT]->(b:Entity {id: $target_id})
                RETURN r
                """,
                source_id=source_id,
                target_id=target_id
            )
            record = await result.single()
            assert record is not None

    async def test_find_connected_entities_depth_1(self, graph_db):
        """Test finding entities connected at depth 1."""
        # Create a simple graph: A -> B -> C
        await graph_db.create_entity("a", "PERSON", "Alice", {})
        await graph_db.create_entity("b", "ORG", "Microsoft", {})
        await graph_db.create_entity("c", "PRODUCT", "Windows", {})
        
        await graph_db.create_relationship("a", "b", "WORKS_AT", {})
        await graph_db.create_relationship("b", "c", "CREATES", {})
        
        # Find entities connected to A at depth 1
        connected = await graph_db.find_connected_entities(
            entity_id="a",
            max_depth=1
        )
        
        # Should find B but not C
        assert len(connected) > 0
        entity_ids = [c["connected"]["id"] for c in connected]
        assert "b" in entity_ids
        assert "c" not in entity_ids

    async def test_find_connected_entities_depth_2(self, graph_db):
        """Test finding entities connected at depth 2."""
        # Create a simple graph: A -> B -> C
        await graph_db.create_entity("a", "PERSON", "Alice", {})
        await graph_db.create_entity("b", "ORG", "Microsoft", {})
        await graph_db.create_entity("c", "PRODUCT", "Windows", {})
        
        await graph_db.create_relationship("a", "b", "WORKS_AT", {})
        await graph_db.create_relationship("b", "c", "CREATES", {})
        
        # Find entities connected to A at depth 2
        connected = await graph_db.find_connected_entities(
            entity_id="a",
            max_depth=2
        )
        
        # Should find both B and C
        assert len(connected) >= 2
        entity_ids = [c["connected"]["id"] for c in connected]
        assert "b" in entity_ids
        assert "c" in entity_ids

    async def test_find_connected_entities_with_type_filter(self, graph_db):
        """Test finding connected entities filtered by relationship type."""
        # Create graph with multiple relationship types
        await graph_db.create_entity("person1", "PERSON", "Alice", {})
        await graph_db.create_entity("org1", "ORG", "Microsoft", {})
        await graph_db.create_entity("person2", "PERSON", "Bob", {})
        
        await graph_db.create_relationship("person1", "org1", "WORKS_AT", {})
        await graph_db.create_relationship("person1", "person2", "KNOWS", {})
        
        # Find only WORKS_AT relationships
        connected = await graph_db.find_connected_entities(
            entity_id="person1",
            max_depth=1,
            relationship_types=["WORKS_AT"]
        )
        
        # Should find org1 but not person2
        entity_ids = [c["connected"]["id"] for c in connected]
        assert "org1" in entity_ids
        assert "person2" not in entity_ids

    async def test_search_entities_by_text(self, graph_db):
        """Test searching for entities by text content."""
        # Create test entities
        await graph_db.create_entity("e1", "PERSON", "Alice Johnson", {})
        await graph_db.create_entity("e2", "PERSON", "Alice Smith", {})
        await graph_db.create_entity("e3", "PERSON", "Bob Johnson", {})
        
        # Search for "Alice"
        results = await graph_db.search_entities(
            query="Alice",
            limit=10
        )
        
        # Should find 2 entities with "Alice"
        assert len(results) == 2
        texts = [r["text"] for r in results]
        assert "Alice Johnson" in texts
        assert "Alice Smith" in texts
        assert "Bob Johnson" not in texts

    async def test_search_entities_with_type_filter(self, graph_db):
        """Test searching entities with type filtering."""
        # Create mixed entity types
        await graph_db.create_entity("e1", "PERSON", "Microsoft Bob", {})
        await graph_db.create_entity("e2", "ORG", "Microsoft Corporation", {})
        
        # Search for "Microsoft" but only ORG type
        results = await graph_db.search_entities(
            query="Microsoft",
            entity_types=["ORG"],
            limit=10
        )
        
        # Should only find the ORG entity
        assert len(results) == 1
        assert results[0]["type"] == "ORG"
        assert results[0]["text"] == "Microsoft Corporation"

    async def test_search_entities_with_limit(self, graph_db):
        """Test search limit parameter."""
        # Create multiple entities
        for i in range(10):
            await graph_db.create_entity(
                f"test_{i}",
                "PERSON",
                f"Test Person {i}",
                {}
            )
        
        # Search with limit
        results = await graph_db.search_entities(
            query="Test",
            limit=5
        )
        
        # Should respect limit
        assert len(results) <= 5

    async def test_empty_results_for_nonexistent_entity(self, graph_db):
        """Test that searching for nonexistent entity returns empty."""
        results = await graph_db.find_connected_entities(
            entity_id="nonexistent_entity",
            max_depth=1
        )
        
        # Should return empty list
        assert results == []
