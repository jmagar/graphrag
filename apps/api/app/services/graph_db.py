"""
Neo4j graph database service.

Manages entity and relationship storage in a knowledge graph.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.core.config import settings

logger = logging.getLogger(__name__)


class GraphDBService:
    """Service for Neo4j graph database operations."""

    def __init__(self):
        """Initialize GraphDBService (actual connection happens in initialize())."""
        self.driver: Optional[AsyncDriver] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize Neo4j driver and create indexes.

        This must be called before using any other methods.
        """
        if self._initialized:
            logger.warning("GraphDBService already initialized")
            return

        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

            # Verify connection
            await self.driver.verify_connectivity()

            # Create indexes for performance
            await self._create_indexes()

            self._initialized = True
            logger.info(f"✅ Connected to Neo4j at {settings.NEO4J_URI}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            raise

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self.driver:
            await self.driver.close()
            self._initialized = False
            logger.info("Closed Neo4j connection")

    async def _create_indexes(self) -> None:
        """Create indexes on Entity nodes for performance."""
        async with self.driver.session() as session:
            # Index on entity ID (for fast lookups)
            await session.run("CREATE INDEX entity_id_index IF NOT EXISTS FOR (e:Entity) ON (e.id)")

            # Index on entity text (for text search)
            await session.run(
                "CREATE INDEX entity_text_index IF NOT EXISTS FOR (e:Entity) ON (e.text)"
            )

            # Index on entity type (for type filtering)
            await session.run(
                "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)"
            )

        logger.debug("Created Neo4j indexes")

    async def create_entity(
        self, entity_id: str, entity_type: str, text: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create or update an entity node in the graph.

        Uses MERGE to avoid duplicates (idempotent operation).

        Args:
            entity_id: Unique identifier for the entity
            entity_type: Entity type (PERSON, ORG, LOCATION, etc.)
            text: Entity text content
            metadata: Additional metadata dictionary

        Returns:
            Dictionary with entity properties

        Example:
            >>> await graph_db.create_entity(
            ...     entity_id="person_1",
            ...     entity_type="PERSON",
            ...     text="Alice Johnson",
            ...     metadata={"confidence": 0.9}
            ... )
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        # Serialize metadata to JSON string for storage
        metadata_json = json.dumps(metadata) if metadata else "{}"

        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (e:Entity {id: $entity_id})
                SET e.type = $entity_type,
                    e.text = $text,
                    e.metadata = $metadata_json,
                    e.updated_at = datetime()
                RETURN e
                """,
                entity_id=entity_id,
                entity_type=entity_type,
                text=text,
                metadata_json=metadata_json,
            )
            record = await result.single()

            if record:
                entity_node = record["e"]
                return dict(entity_node)

            return {}

    async def create_relationship(
        self, source_id: str, target_id: str, relationship_type: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a relationship between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Relationship type (WORKS_AT, LOCATED_IN, etc.)
            metadata: Additional relationship metadata

        Returns:
            Dictionary with relationship properties

        Example:
            >>> await graph_db.create_relationship(
            ...     source_id="person_1",
            ...     target_id="org_1",
            ...     relationship_type="WORKS_AT",
            ...     metadata={"since": 2020}
            ... )
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        # Serialize metadata to JSON string for storage
        metadata_json = json.dumps(metadata) if metadata else "{}"

        async with self.driver.session() as session:
            # Use dynamic relationship type (Cypher doesn't allow parameterized relationship types)
            # So we need to use string formatting (safe here as relationship_type is controlled)
            query = f"""
            MATCH (a:Entity {{id: $source_id}})
            MATCH (b:Entity {{id: $target_id}})
            MERGE (a)-[r:{relationship_type}]->(b)
            SET r.metadata = $metadata_json,
                r.created_at = datetime()
            RETURN r
            """

            result = await session.run(
                query, source_id=source_id, target_id=target_id, metadata_json=metadata_json
            )
            record = await result.single()

            if record:
                rel = record["r"]
                return dict(rel)

            return {}

    async def find_connected_entities(
        self, entity_id: str, max_depth: int = 2, relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find entities connected to a given entity via graph traversal.

        Args:
            entity_id: Starting entity ID
            max_depth: Maximum traversal depth (1-4 recommended)
            relationship_types: Optional filter on relationship types

        Returns:
            List of dictionaries with 'connected', 'relationship_path', 'distance'

        Example:
            >>> connected = await graph_db.find_connected_entities(
            ...     entity_id="person_1",
            ...     max_depth=2,
            ...     relationship_types=["WORKS_AT", "KNOWS"]
            ... )
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        # Build relationship type filter
        rel_filter = ""
        if relationship_types:
            rel_filter = f":{('|'.join(relationship_types))}"

        async with self.driver.session() as session:
            query = f"""
            MATCH (start:Entity {{id: $entity_id}})
            MATCH path = (start)-[r{rel_filter}*1..{max_depth}]-(connected)
            WHERE connected.id <> start.id
            RETURN DISTINCT connected,
                   [rel in relationships(path) | type(rel)] as relationship_path,
                   length(path) as distance
            ORDER BY distance
            """

            result = await session.run(query, entity_id=entity_id)

            connected_entities = []
            async for record in result:
                connected_entities.append(
                    {
                        "connected": dict(record["connected"]),
                        "relationship_path": record["relationship_path"],
                        "distance": record["distance"],
                    }
                )

            return connected_entities

    async def search_entities(
        self, query: str, entity_types: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for entities by text content.

        Args:
            query: Search query string
            entity_types: Optional filter on entity types
            limit: Maximum number of results

        Returns:
            List of entity dictionaries matching the query

        Example:
            >>> entities = await graph_db.search_entities(
            ...     query="Alice",
            ...     entity_types=["PERSON"],
            ...     limit=10
            ... )
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        # Build combined WHERE clause
        where_clauses = ["e.text CONTAINS $search_text"]
        if entity_types:
            where_clauses.append(f"e.type IN {entity_types}")
        where_clause = " AND ".join(where_clauses)

        async with self.driver.session() as session:
            cypher_query = f"""
            MATCH (e:Entity)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.text
            LIMIT $limit
            """

            result = await session.run(cypher_query, search_text=query, limit=limit)

            entities = []
            async for record in result:
                entities.append(dict(record["e"]))

            return entities

    async def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single entity by ID.

        Args:
            entity_id: Entity ID to retrieve

        Returns:
            Entity dictionary or None if not found
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {id: $entity_id}) RETURN e", entity_id=entity_id
            )
            record = await result.single()

            if record:
                return dict(record["e"])

            return None

    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity and all its relationships.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $entity_id})
                DETACH DELETE e
                RETURN count(e) as deleted_count
                """,
                entity_id=entity_id,
            )
            record = await result.single()

            return record["deleted_count"] > 0 if record else False

    async def get_stats(self) -> Dict[str, int]:
        """
        Get graph database statistics.

        Returns:
            Dictionary with node counts and relationship counts
        """
        if not self._initialized:
            raise RuntimeError("GraphDBService not initialized. Call initialize() first.")

        async with self.driver.session() as session:
            # Count entities
            entity_result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_record = await entity_result.single()
            entity_count = entity_record["count"] if entity_record else 0

            # Count relationships
            rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_record = await rel_result.single()
            rel_count = rel_record["count"] if rel_record else 0

            return {"entities": entity_count, "relationships": rel_count}
