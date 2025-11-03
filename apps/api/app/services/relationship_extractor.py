"""
Relationship extraction service using LLM.

Extracts semantic relationships between entities in text.
"""

import json
import logging
from typing import List, Dict, Any, Tuple
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


# Common relationship types
RELATIONSHIP_TYPES = [
    "WORKS_AT",         # Person works at organization
    "WORKS_FOR",        # Person works for organization
    "EMPLOYED_BY",      # Person employed by organization
    "LOCATED_IN",       # Entity located in place
    "BASED_IN",         # Organization based in location
    "COLLABORATES_WITH", # Person collaborates with person
    "WORKS_WITH",       # Person works with person
    "KNOWS",            # Person knows person
    "CREATES",          # Entity creates product/work
    "BUILDS",           # Entity builds product
    "DEVELOPS",         # Entity develops product
    "PART_OF",          # Entity is part of larger entity
    "MEMBER_OF",        # Person is member of organization
    "MANAGES",          # Person manages entity
    "LEADS",            # Person leads entity/project
    "FOUNDED",          # Person founded organization
    "OWNS",             # Entity owns entity
    "USES",             # Entity uses product/technology
    "IMPLEMENTS",       # Entity implements technology
]


class RelationshipExtractor:
    """Extract relationships between entities using LLM."""

    def __init__(self):
        """Initialize the relationship extractor with LLM service."""
        self.llm_service = LLMService()
        logger.info("Initialized RelationshipExtractor with LLM service")

    async def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, str]]:
        """
        Extract relationships between entities in text using LLM.

        Args:
            text: The text containing entities
            entities: List of entity dictionaries with 'text' and 'type' fields

        Returns:
            List of (source, relation, target) tuples

        Example:
            >>> extractor = RelationshipExtractor()
            >>> text = "Alice Johnson works at Microsoft."
            >>> entities = [
            ...     {"text": "Alice Johnson", "type": "PERSON"},
            ...     {"text": "Microsoft", "type": "ORG"}
            ... ]
            >>> relationships = await extractor.extract_relationships(text, entities)
            >>> relationships
            [("Alice Johnson", "WORKS_AT", "Microsoft")]
        """
        # Handle edge cases
        if not entities or len(entities) < 2:
            return []

        if not text or not text.strip():
            return []

        # Build entity list for prompt
        entity_list = [f"{e['text']} ({e['type']})" for e in entities]
        entity_names = [e['text'] for e in entities]

        # Build prompt for LLM
        prompt = self._build_extraction_prompt(text, entity_list)

        try:
            # Call LLM to extract relationships
            # Use generate_response with empty context (prompt contains all info)
            response = await self.llm_service.generate_response(
                query=prompt,
                context="",
                system_prompt="You are a relationship extraction assistant. Extract only the relationships requested and return them in the specified JSON format."
            )

            # Parse LLM response
            relationships = self._parse_llm_response(response, entity_names)

            logger.debug(
                f"Extracted {len(relationships)} relationships from text "
                f"with {len(entities)} entities"
            )

            return relationships

        except Exception as e:
            logger.error(f"Failed to extract relationships: {e}")
            return []

    def _build_extraction_prompt(
        self,
        text: str,
        entity_list: List[str]
    ) -> str:
        """
        Build a prompt for the LLM to extract relationships.

        Args:
            text: The source text
            entity_list: List of formatted entity strings

        Returns:
            Formatted prompt string
        """
        relationship_examples = ", ".join(RELATIONSHIP_TYPES[:10])

        prompt = f"""Extract relationships between entities in the following text.

Text: {text}

Entities found: {', '.join(entity_list)}

Identify semantic relationships between these entities. For each relationship, provide:
- Source entity (exact text match from entities list)
- Relationship type (e.g., {relationship_examples}, etc.)
- Target entity (exact text match from entities list)

Common relationship types:
- WORKS_AT, WORKS_FOR, EMPLOYED_BY (employment)
- LOCATED_IN, BASED_IN (location)
- COLLABORATES_WITH, WORKS_WITH, KNOWS (collaboration)
- CREATES, BUILDS, DEVELOPS (creation)
- PART_OF, MEMBER_OF (membership)
- MANAGES, LEADS (management)
- USES, IMPLEMENTS (usage)

Return ONLY a JSON array in this exact format, with no other text:
[
    {{"source": "entity1", "relation": "RELATIONSHIP_TYPE", "target": "entity2"}},
    {{"source": "entity3", "relation": "RELATIONSHIP_TYPE", "target": "entity4"}}
]

Rules:
- Only extract relationships explicitly stated or strongly implied in the text
- Use exact entity names from the entities list
- Use relationship types that best describe the connection
- If no clear relationships exist, return an empty array: []
"""
        return prompt

    def _parse_llm_response(
        self,
        response: str,
        entity_names: List[str]
    ) -> List[Tuple[str, str, str]]:
        """
        Parse LLM response into relationship tuples.

        Args:
            response: Raw LLM response text
            entity_names: List of valid entity names

        Returns:
            List of (source, relation, target) tuples
        """
        relationships = []

        try:
            # Clean response - extract JSON array
            response = response.strip()

            # Try to find JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']')

            if start_idx == -1 or end_idx == -1:
                logger.warning("No JSON array found in LLM response")
                return []

            json_str = response[start_idx:end_idx + 1]
            parsed = json.loads(json_str)

            # Validate and convert to tuples
            for item in parsed:
                if not isinstance(item, dict):
                    continue

                source = item.get("source", "").strip()
                relation = item.get("relation", "").strip()
                target = item.get("target", "").strip()

                # Validate all fields are present
                if not (source and relation and target):
                    continue

                # Validate entities are in the original entity list
                if source not in entity_names or target not in entity_names:
                    logger.debug(
                        f"Skipping relationship with invalid entities: "
                        f"{source} -> {target}"
                    )
                    continue

                # Skip self-references
                if source == target:
                    continue

                relationships.append((source, relation, target))

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")

        return relationships

    def get_relationship_types(self) -> List[str]:
        """
        Get list of common relationship types.

        Returns:
            List of relationship type strings
        """
        return RELATIONSHIP_TYPES.copy()
