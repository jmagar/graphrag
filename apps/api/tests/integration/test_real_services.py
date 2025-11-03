"""
Integration tests with real services (Qdrant, Redis, Neo4j).

These tests require docker-compose.test.yml to be running:
    docker-compose -f docker-compose.test.yml up -d

Run with:
    pytest tests/integration/test_real_services.py -v
"""

import pytest
import asyncio
from qdrant_client import AsyncQdrantClient, models
from redis import asyncio as aioredis
from neo4j import AsyncGraphDatabase

# Test configuration
QDRANT_URL = "http://localhost:4203"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "testpassword123"


@pytest.mark.integration
class TestQdrantIntegration:
    """Integration tests with real Qdrant instance."""

    @pytest.fixture
    async def qdrant_client(self):
        """Create Qdrant client."""
        client = AsyncQdrantClient(url=QDRANT_URL)
        yield client
        await client.close()

    @pytest.mark.anyio
    async def test_qdrant_health_check(self, qdrant_client):
        """Test Qdrant is accessible and healthy."""
        # Health check should not raise
        try:
            collections = await qdrant_client.get_collections()
            assert collections is not None
        except Exception as e:
            pytest.fail(f"Qdrant health check failed: {e}")

    @pytest.mark.anyio
    async def test_qdrant_create_collection(self, qdrant_client):
        """Test creating a collection in Qdrant."""
        collection_name = "test_collection"

        # Clean up if exists
        try:
            await qdrant_client.delete_collection(collection_name)
        except:
            pass

        # Create collection
        await qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )

        # Verify exists
        collection_info = await qdrant_client.get_collection(collection_name)
        assert collection_info.config.params.vectors.size == 768

        # Cleanup
        await qdrant_client.delete_collection(collection_name)

    @pytest.mark.anyio
    async def test_qdrant_upsert_and_search(self, qdrant_client):
        """Test upserting and searching vectors."""
        collection_name = "test_search"

        # Clean up if exists
        try:
            await qdrant_client.delete_collection(collection_name)
        except:
            pass

        # Create collection
        await qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE)
        )

        # Upsert some points
        await qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id="test1",
                    vector=[1.0, 0.0, 0.0],
                    payload={"content": "Document 1"}
                ),
                models.PointStruct(
                    id="test2",
                    vector=[0.0, 1.0, 0.0],
                    payload={"content": "Document 2"}
                )
            ]
        )

        # Search
        results = await qdrant_client.search(
            collection_name=collection_name,
            query_vector=[1.0, 0.0, 0.0],
            limit=2
        )

        assert len(results) == 2
        assert results[0].id == "test1"
        assert results[0].payload["content"] == "Document 1"

        # Cleanup
        await qdrant_client.delete_collection(collection_name)


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests with real Redis instance."""

    @pytest.fixture
    async def redis_client(self):
        """Create Redis client."""
        client = await aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}",
            decode_responses=True
        )
        yield client
        await client.aclose()

    @pytest.mark.anyio
    async def test_redis_ping(self, redis_client):
        """Test Redis is accessible."""
        pong = await redis_client.ping()
        assert pong is True

    @pytest.mark.anyio
    async def test_redis_set_get(self, redis_client):
        """Test basic set/get operations."""
        key = "test:key"
        value = "test_value"

        await redis_client.set(key, value)
        result = await redis_client.get(key)

        assert result == value

        # Cleanup
        await redis_client.delete(key)

    @pytest.mark.anyio
    async def test_redis_set_operations(self, redis_client):
        """Test Redis set operations (used for deduplication)."""
        set_key = "test:crawl:processed"

        # Add members
        await redis_client.sadd(set_key, "url1", "url2", "url3")

        # Check membership
        is_member = await redis_client.sismember(set_key, "url1")
        assert is_member is True

        not_member = await redis_client.sismember(set_key, "url4")
        assert not_member is False

        # Get count
        count = await redis_client.scard(set_key)
        assert count == 3

        # Cleanup
        await redis_client.delete(set_key)

    @pytest.mark.anyio
    async def test_redis_expiration(self, redis_client):
        """Test TTL/expiration (used for tracking cleanup)."""
        key = "test:expiring"

        await redis_client.set(key, "value", ex=1)  # 1 second TTL

        # Key should exist immediately
        assert await redis_client.exists(key) == 1

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Key should be gone
        assert await redis_client.exists(key) == 0


@pytest.mark.integration
class TestNeo4jIntegration:
    """Integration tests with real Neo4j instance."""

    @pytest.fixture
    async def neo4j_driver(self):
        """Create Neo4j driver."""
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        yield driver
        await driver.close()

    @pytest.mark.anyio
    async def test_neo4j_connection(self, neo4j_driver):
        """Test Neo4j is accessible."""
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1 AS num")
            record = await result.single()
            assert record["num"] == 1

    @pytest.mark.anyio
    async def test_neo4j_create_node(self, neo4j_driver):
        """Test creating and querying nodes."""
        async with neo4j_driver.session() as session:
            # Create node
            await session.run(
                "CREATE (n:TestEntity {id: $id, name: $name})",
                id="test123",
                name="Test Entity"
            )

            # Query node
            result = await session.run(
                "MATCH (n:TestEntity {id: $id}) RETURN n.name AS name",
                id="test123"
            )
            record = await result.single()
            assert record["name"] == "Test Entity"

            # Cleanup
            await session.run("MATCH (n:TestEntity {id: $id}) DELETE n", id="test123")

    @pytest.mark.anyio
    async def test_neo4j_create_relationship(self, neo4j_driver):
        """Test creating relationships between nodes."""
        async with neo4j_driver.session() as session:
            # Create two nodes and a relationship
            await session.run("""
                CREATE (a:TestEntity {id: $id1, name: $name1})
                CREATE (b:TestEntity {id: $id2, name: $name2})
                CREATE (a)-[:RELATED_TO]->(b)
            """, id1="test1", name1="Entity 1", id2="test2", name2="Entity 2")

            # Query relationship
            result = await session.run("""
                MATCH (a:TestEntity {id: $id1})-[:RELATED_TO]->(b:TestEntity)
                RETURN b.name AS name
            """, id1="test1")
            record = await result.single()
            assert record["name"] == "Entity 2"

            # Cleanup
            await session.run("""
                MATCH (n:TestEntity) WHERE n.id IN [$id1, $id2]
                DETACH DELETE n
            """, id1="test1", id2="test2")

    @pytest.mark.anyio
    async def test_neo4j_graph_traversal(self, neo4j_driver):
        """Test graph traversal (used for connected entities)."""
        async with neo4j_driver.session() as session:
            # Create chain: A -> B -> C
            await session.run("""
                CREATE (a:TestEntity {id: 'a', name: 'A'})
                CREATE (b:TestEntity {id: 'b', name: 'B'})
                CREATE (c:TestEntity {id: 'c', name: 'C'})
                CREATE (a)-[:CONNECTS]->(b)
                CREATE (b)-[:CONNECTS]->(c)
            """)

            # Traverse from A with depth 2
            result = await session.run("""
                MATCH path = (start:TestEntity {id: 'a'})-[:CONNECTS*1..2]->(end:TestEntity)
                RETURN end.name AS name, length(path) AS depth
                ORDER BY depth
            """)

            records = [record async for record in result]
            assert len(records) == 2
            assert records[0]["name"] == "B"
            assert records[0]["depth"] == 1
            assert records[1]["name"] == "C"
            assert records[1]["depth"] == 2

            # Cleanup
            await session.run("""
                MATCH (n:TestEntity) WHERE n.id IN ['a', 'b', 'c']
                DETACH DELETE n
            """)


@pytest.mark.integration
@pytest.mark.anyio
async def test_all_services_healthy():
    """
    Meta-test: Verify all services are accessible.

    This test should run first to ensure docker-compose is running.
    """
    services_status = {}

    # Test Qdrant
    try:
        qdrant = AsyncQdrantClient(url=QDRANT_URL)
        await qdrant.get_collections()
        await qdrant.close()
        services_status["qdrant"] = "✅ healthy"
    except Exception as e:
        services_status["qdrant"] = f"❌ unhealthy: {e}"

    # Test Redis
    try:
        redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}")
        await redis.ping()
        await redis.aclose()
        services_status["redis"] = "✅ healthy"
    except Exception as e:
        services_status["redis"] = f"❌ unhealthy: {e}"

    # Test Neo4j
    try:
        neo4j = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        async with neo4j.session() as session:
            await session.run("RETURN 1")
        await neo4j.close()
        services_status["neo4j"] = "✅ healthy"
    except Exception as e:
        services_status["neo4j"] = f"❌ unhealthy: {e}"

    # Report status
    print("\n=== Service Health Status ===")
    for service, status in services_status.items():
        print(f"{service}: {status}")

    # Fail if any service is unhealthy
    unhealthy = [s for s, status in services_status.items() if "❌" in status]
    if unhealthy:
        pytest.fail(
            f"Services unhealthy: {', '.join(unhealthy)}\n"
            "Run: docker-compose -f docker-compose.test.yml up -d"
        )
