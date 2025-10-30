# Phase 2: Knowledge Graph Core

**Status**: 🔵 Not Started (Blocked by Phase 1)  
**Duration**: 4 weeks (Weeks 5-8)  
**Priority**: High  
**Prerequisites**: Phase 1 complete

---

## 🎯 Objectives

Transform the system from traditional vector-only RAG into true **GraphRAG** by adding entity extraction, knowledge graph storage, and hybrid retrieval (vector + graph).

### Success Criteria
- ✅ Entity extraction from documents (85%+ precision)
- ✅ Neo4j graph database integrated
- ✅ Relationship extraction working
- ✅ Hybrid queries (vector + graph) < 1 second
- ✅ Graph improves answer quality 30%+ vs vector-only
- ✅ All features tested (80%+ coverage)

---

## 📋 Core Concepts

### What is GraphRAG?
Traditional RAG uses only **vector similarity** for retrieval. GraphRAG adds:
1. **Entity Recognition**: Extract people, places, concepts from documents
2. **Relationship Mapping**: Connect entities (e.g., "Alice WORKS_AT Company")
3. **Graph Traversal**: Navigate relationships to find relevant context
4. **Hybrid Retrieval**: Combine vector search + graph traversal

### Example Scenario
**User Query**: "What projects has Alice worked on?"

**Traditional RAG** (vector only):
- Finds documents mentioning "Alice" and "projects"
- Misses indirect connections
- No structured relationships

**GraphRAG** (hybrid):
- Finds Alice entity in graph
- Traverses `WORKS_ON` relationships
- Retrieves all connected project entities
- Enhances with vector-similar project descriptions
- Returns comprehensive, connected answer

---

## 🏗️ Architecture

### Data Flow
```
Document → Entity Extraction → Graph Storage → Hybrid Query → Response
            ↓                      ↓               ↓
         Embeddings           Neo4j          Vector DB
                                 ↓               ↓
                            Graph Query    Semantic Search
                                 ↓               ↓
                                 └─────┬─────────┘
                                       ↓
                                  Combined Results
```

### Component Overview
1. **Entity Extractor** (spaCy + LLM validation)
2. **Graph Database** (Neo4j)
3. **Relationship Extractor** (LLM-based)
4. **Hybrid Query Engine** (orchestrator)
5. **Graph Query API** (endpoints)

---

## 📦 Deliverable 1: Entity Extraction Pipeline

### spaCy NER Setup
```python
# apps/api/app/services/entity_extractor.py
import spacy
from typing import List, Dict, Any
from app.services.llm import LLMService

class EntityExtractor:
    """Extract entities from text using spaCy NER + LLM validation."""
    
    def __init__(self):
        # Load spaCy model (en_core_web_lg for best accuracy)
        self.nlp = spacy.load("en_core_web_lg")
        self.llm_service = LLMService()
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text.
        
        Returns:
            [
                {
                    "text": "Alice Johnson",
                    "type": "PERSON",
                    "start": 0,
                    "end": 13,
                    "confidence": 0.95
                },
                ...
            ]
        """
        # Step 1: spaCy NER
        doc = self.nlp(text)
        spacy_entities = [
            {
                "text": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": 0.8  # Default confidence for spaCy
            }
            for ent in doc.ents
            if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "WORK_OF_ART"]
        ]
        
        # Step 2: LLM validation (for ambiguous entities)
        validated_entities = await self._validate_with_llm(text, spacy_entities)
        
        return validated_entities
    
    async def _validate_with_llm(
        self, 
        text: str, 
        entities: List[Dict]
    ) -> List[Dict]:
        """Use LLM to validate and refine entity extraction."""
        # Only validate low-confidence or ambiguous entities
        ambiguous = [e for e in entities if e["confidence"] < 0.9]
        
        if not ambiguous:
            return entities
        
        # Build validation prompt
        prompt = f"""
        Text: {text}
        
        Potential entities: {[e['text'] for e in ambiguous]}
        
        For each entity, determine:
        1. Is it actually an entity? (yes/no)
        2. What type is it? (PERSON, ORG, LOCATION, CONCEPT, etc.)
        3. Confidence (0-1)
        
        Return JSON array.
        """
        
        # Get LLM validation
        validation = await self.llm_service.generate_structured_response(
            prompt=prompt,
            schema={"type": "array", "items": {"type": "object"}}
        )
        
        # Merge validated entities
        return self._merge_validations(entities, validation)
```

### Entity Types
```python
ENTITY_TYPES = [
    "PERSON",           # People (Alice Johnson, Dr. Smith)
    "ORGANIZATION",     # Companies, institutions (Microsoft, MIT)
    "LOCATION",         # Places (Seattle, Office 405)
    "CONCEPT",          # Abstract ideas (Machine Learning, GraphRAG)
    "PRODUCT",          # Products, tools (Python, Neo4j)
    "EVENT",            # Events (Conference 2023, Launch)
    "WORK_OF_ART",      # Documents, papers, books
    "DATE",             # Temporal entities
]
```

---

## 📦 Deliverable 2: Neo4j Integration

### Graph Database Service
```python
# apps/api/app/services/graph_db.py
from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any
from app.core.config import settings

class GraphDBService:
    """Service for Neo4j graph database operations."""
    
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    async def create_entity(
        self, 
        entity_id: str,
        entity_type: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an entity node in the graph."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (e:Entity {id: $entity_id})
                SET e.type = $entity_type,
                    e.text = $text,
                    e.metadata = $metadata,
                    e.updated_at = datetime()
                RETURN e
                """,
                entity_id=entity_id,
                entity_type=entity_type,
                text=text,
                metadata=metadata
            )
            return await result.single()
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a relationship between two entities."""
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (a:Entity {{id: $source_id}})
                MATCH (b:Entity {{id: $target_id}})
                MERGE (a)-[r:{relationship_type}]->(b)
                SET r.metadata = $metadata,
                    r.created_at = datetime()
                RETURN r
                """,
                source_id=source_id,
                target_id=target_id,
                metadata=metadata
            )
            return await result.single()
    
    async def find_connected_entities(
        self,
        entity_id: str,
        max_depth: int = 2,
        relationship_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Find entities connected to a given entity."""
        rel_filter = ""
        if relationship_types:
            rel_filter = f":{('|'.join(relationship_types))}"
        
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (start:Entity {{id: $entity_id}})
                MATCH path = (start)-[r{rel_filter}*1..{max_depth}]-(connected)
                RETURN DISTINCT connected, 
                       [rel in relationships(path) | type(rel)] as relationship_path,
                       length(path) as distance
                ORDER BY distance
                """,
                entity_id=entity_id
            )
            return [record async for record in result]
    
    async def search_entities(
        self,
        query: str,
        entity_types: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for entities by text."""
        type_filter = ""
        if entity_types:
            type_filter = f"WHERE e.type IN {entity_types}"
        
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (e:Entity)
                {type_filter}
                WHERE e.text CONTAINS $query
                RETURN e
                LIMIT $limit
                """,
                query=query,
                limit=limit
            )
            return [record["e"] async for record in result]
```

### Graph Schema
```cypher
// Entity nodes
CREATE (e:Entity {
    id: "uuid",
    type: "PERSON|ORG|LOCATION|CONCEPT|...",
    text: "Entity name",
    metadata: {},
    created_at: datetime(),
    updated_at: datetime()
})

// Document nodes
CREATE (d:Document {
    id: "uuid",
    url: "https://...",
    title: "Document title",
    created_at: datetime()
})

// Relationships
(:Entity)-[:MENTIONED_IN]->(:Document)
(:Entity)-[:RELATED_TO {type: "works_with"}]->(:Entity)
(:Entity)-[:WORKS_AT]->(:Entity:ORG)
(:Entity)-[:LOCATED_IN]->(:Entity:LOCATION)
(:Entity)-[:PART_OF]->(:Entity)

// Indexes
CREATE INDEX entity_id FOR (e:Entity) ON (e.id)
CREATE INDEX entity_text FOR (e:Entity) ON (e.text)
CREATE INDEX entity_type FOR (e:Entity) ON (e.type)
```

---

## 📦 Deliverable 3: Relationship Extraction

### Relationship Extractor
```python
# apps/api/app/services/relationship_extractor.py
from typing import List, Dict, Tuple
from app.services.llm import LLMService

class RelationshipExtractor:
    """Extract relationships between entities using LLM."""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    async def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, str]]:
        """
        Extract relationships between entities in text.
        
        Returns:
            [
                ("Alice Johnson", "WORKS_AT", "Microsoft"),
                ("Alice Johnson", "COLLABORATES_WITH", "Bob Smith"),
                ...
            ]
        """
        # Build prompt with entities
        entity_list = [e["text"] for e in entities]
        
        prompt = f"""
        Text: {text}
        
        Entities found: {entity_list}
        
        Identify relationships between these entities.
        For each relationship, provide:
        - Source entity
        - Relationship type (e.g., WORKS_AT, COLLABORATES_WITH, LOCATED_IN)
        - Target entity
        
        Return as JSON array: [
            {{"source": "entity1", "relation": "TYPE", "target": "entity2"}},
            ...
        ]
        
        Common relationship types:
        - WORKS_AT, WORKS_FOR
        - LOCATED_IN, BASED_IN
        - COLLABORATES_WITH, WORKS_WITH
        - CREATES, BUILDS, DEVELOPS
        - PART_OF, MEMBER_OF
        - MANAGES, LEADS
        - USES, IMPLEMENTS
        """
        
        relationships = await self.llm_service.generate_structured_response(
            prompt=prompt,
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "relation": {"type": "string"},
                        "target": {"type": "string"}
                    }
                }
            }
        )
        
        return [
            (r["source"], r["relation"], r["target"])
            for r in relationships
        ]
```

---

## 📦 Deliverable 4: Hybrid Query System

### Hybrid Query Engine
```python
# apps/api/app/services/hybrid_query.py
from typing import List, Dict, Any
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
from app.services.graph_db import GraphDBService

class HybridQueryEngine:
    """Orchestrate hybrid queries across vector and graph databases."""
    
    def __init__(self):
        self.embeddings_service = EmbeddingsService()
        self.vector_db_service = VectorDBService()
        self.graph_db_service = GraphDBService()
    
    async def hybrid_search(
        self,
        query: str,
        vector_limit: int = 5,
        graph_depth: int = 2,
        rerank: bool = True
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector and graph retrieval.
        
        Steps:
        1. Extract entities from query
        2. Vector search for semantically similar documents
        3. Graph search for connected entities
        4. Combine and rerank results
        5. Return unified results
        """
        # Step 1: Extract query entities
        from app.services.entity_extractor import EntityExtractor
        entity_extractor = EntityExtractor()
        query_entities = await entity_extractor.extract_entities(query)
        
        # Step 2: Vector search
        query_embedding = await self.embeddings_service.generate_embedding(query)
        vector_results = await self.vector_db_service.search(
            query_embedding=query_embedding,
            limit=vector_limit
        )
        
        # Step 3: Graph search (if entities found)
        graph_results = []
        for entity in query_entities:
            # Find entity in graph
            entity_nodes = await self.graph_db_service.search_entities(
                query=entity["text"],
                limit=1
            )
            
            if entity_nodes:
                # Get connected entities
                connected = await self.graph_db_service.find_connected_entities(
                    entity_id=entity_nodes[0]["id"],
                    max_depth=graph_depth
                )
                graph_results.extend(connected)
        
        # Step 4: Combine results
        combined_results = self._combine_results(
            vector_results=vector_results,
            graph_results=graph_results
        )
        
        # Step 5: Rerank (optional)
        if rerank:
            combined_results = await self._rerank_results(query, combined_results)
        
        return {
            "query": query,
            "query_entities": query_entities,
            "vector_results": vector_results,
            "graph_results": graph_results,
            "combined_results": combined_results,
            "retrieval_strategy": "hybrid"
        }
    
    def _combine_results(
        self,
        vector_results: List[Dict],
        graph_results: List[Dict]
    ) -> List[Dict]:
        """Combine and deduplicate results from vector and graph search."""
        # Merge by document ID
        results_map = {}
        
        for result in vector_results:
            doc_id = result["id"]
            results_map[doc_id] = {
                **result,
                "vector_score": result["score"],
                "graph_distance": None,
                "source": "vector"
            }
        
        for result in graph_results:
            doc_id = result.get("id")
            if doc_id in results_map:
                # Enhance existing result
                results_map[doc_id]["graph_distance"] = result.get("distance")
                results_map[doc_id]["source"] = "both"
            else:
                # Add new graph-only result
                results_map[doc_id] = {
                    **result,
                    "vector_score": None,
                    "graph_distance": result.get("distance"),
                    "source": "graph"
                }
        
        return list(results_map.values())
    
    async def _rerank_results(
        self,
        query: str,
        results: List[Dict]
    ) -> List[Dict]:
        """Rerank combined results using a scoring function."""
        # Simple scoring: prefer results from both sources
        for result in results:
            score = 0
            
            # Vector score contribution
            if result["vector_score"]:
                score += result["vector_score"] * 0.6
            
            # Graph distance contribution (closer = better)
            if result["graph_distance"]:
                # Inverse distance (1 = adjacent, 2 = one hop away)
                score += (1.0 / result["graph_distance"]) * 0.4
            
            # Bonus for appearing in both
            if result["source"] == "both":
                score *= 1.2
            
            result["hybrid_score"] = score
        
        # Sort by hybrid score
        results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
        
        return results
```

---

## 📦 Deliverable 5: Graph Query API

### Endpoints
```python
# apps/api/app/api/v1/endpoints/graph.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.hybrid_query import HybridQueryEngine

router = APIRouter()

class HybridQueryRequest(BaseModel):
    query: str
    vector_limit: int = 5
    graph_depth: int = 2
    rerank: bool = True

@router.post("/search")
async def hybrid_search(request: HybridQueryRequest):
    """Perform hybrid search across vector and graph databases."""
    engine = HybridQueryEngine()
    results = await engine.hybrid_search(
        query=request.query,
        vector_limit=request.vector_limit,
        graph_depth=request.graph_depth,
        rerank=request.rerank
    )
    return results

@router.get("/entities/{entity_id}/connections")
async def get_entity_connections(
    entity_id: str,
    max_depth: int = 2
):
    """Get all entities connected to a given entity."""
    from app.services.graph_db import GraphDBService
    graph_db = GraphDBService()
    
    connections = await graph_db.find_connected_entities(
        entity_id=entity_id,
        max_depth=max_depth
    )
    
    return {"entity_id": entity_id, "connections": connections}

@router.get("/entities/search")
async def search_entities(
    q: str,
    types: Optional[List[str]] = None,
    limit: int = 10
):
    """Search for entities by text."""
    from app.services.graph_db import GraphDBService
    graph_db = GraphDBService()
    
    entities = await graph_db.search_entities(
        query=q,
        entity_types=types,
        limit=limit
    )
    
    return {"query": q, "entities": entities}
```

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/services/test_entity_extractor.py
import pytest
from app.services.entity_extractor import EntityExtractor

pytestmark = pytest.mark.anyio

class TestEntityExtractor:
    async def test_extract_person_entities(self):
        """Test extraction of person entities."""
        extractor = EntityExtractor()
        text = "Alice Johnson works at Microsoft with Bob Smith."
        
        entities = await extractor.extract_entities(text)
        
        person_entities = [e for e in entities if e["type"] == "PERSON"]
        assert len(person_entities) >= 2
        assert any("Alice" in e["text"] for e in person_entities)
        assert any("Bob" in e["text"] for e in person_entities)
    
    async def test_extract_organization_entities(self):
        """Test extraction of organization entities."""
        extractor = EntityExtractor()
        text = "Microsoft and Google are competing in AI."
        
        entities = await extractor.extract_entities(text)
        
        org_entities = [e for e in entities if e["type"] in ["ORG", "ORGANIZATION"]]
        assert len(org_entities) >= 2
```

### Integration Tests
```python
# tests/integration/test_hybrid_query.py
import pytest
from app.services.hybrid_query import HybridQueryEngine

pytestmark = pytest.mark.anyio

class TestHybridQuery:
    async def test_hybrid_search_combines_results(self):
        """Test that hybrid search combines vector and graph results."""
        engine = HybridQueryEngine()
        
        results = await engine.hybrid_search(
            query="What projects has Alice worked on?",
            vector_limit=5,
            graph_depth=2
        )
        
        assert "query_entities" in results
        assert "vector_results" in results
        assert "graph_results" in results
        assert "combined_results" in results
        assert results["retrieval_strategy"] == "hybrid"
```

---

## 📦 Dependencies

```toml
# apps/api/pyproject.toml
[tool.poetry.dependencies]
spacy = "^3.7.0"
neo4j = "^5.14.0"

[tool.poetry.group.dev.dependencies]
# Download spaCy model after install
# python -m spacy download en_core_web_lg
```

---

## ✅ Definition of Done

- [ ] Entity extraction achieves 85%+ precision
- [ ] Neo4j integrated and tested
- [ ] Relationships extracted correctly
- [ ] Hybrid queries return in <1 second
- [ ] Graph improves answer quality (measured)
- [ ] All tests pass (80%+ coverage)
- [ ] API endpoints documented
- [ ] Performance benchmarks recorded

---

**Next Phase**: [PHASE_3_VISUALIZATION.md](PHASE_3_VISUALIZATION.md)
