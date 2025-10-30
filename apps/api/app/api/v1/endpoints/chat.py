"""
Chat endpoint with RAG integration and conversation persistence.

Combines:
- Vector search for relevant context
- LLM generation with context
- Conversation and message persistence
"""

from typing import List, Optional, cast
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.database import get_session
from app.db.models import Conversation, Message
from app.services.embeddings import EmbeddingsService
from app.services.vector_db import VectorDBService
from app.services.llm import LLMService

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================


class ChatRequest(BaseModel):
    """Request model for chat."""

    conversation_id: Optional[UUID] = None
    message: str
    use_rag: bool = True
    limit: int = 5


class MessageResponse(BaseModel):
    """Response model for a message."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    sources: List[dict]

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response model for chat."""

    conversation_id: UUID
    message: MessageResponse
    sources: List[dict]


# ============================================================================
# Helper Functions
# ============================================================================


def generate_conversation_title(message: str, max_length: int = 50) -> str:
    """Generate a conversation title from the first message."""
    # Simple truncation for now
    if len(message) <= max_length:
        return message
    return message[: max_length - 3] + "..."


def format_context(search_results: List[dict]) -> str:
    """Format vector search results into context string for LLM."""
    if not search_results:
        return ""

    context_parts = []
    for i, result in enumerate(search_results, 1):
        content = result.get("payload", {}).get("content", "")
        source_url = result.get("payload", {}).get("metadata", {}).get("sourceURL", "Unknown")

        context_parts.append(f"Source {i} ({source_url}):\n{content}")

    return "\n\n".join(context_parts)


# ============================================================================
# Endpoint
# ============================================================================


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_session)):
    """
    Chat with RAG system and conversation persistence.

    Flow:
    1. Get or create conversation
    2. Save user message
    3. If RAG enabled: search vector DB for context
    4. Generate LLM response with context
    5. Save assistant message with sources
    6. Return response
    """
    # Step 1: Get or create conversation
    conversation_id: Optional[UUID] = request.conversation_id

    if conversation_id:
        # Verify conversation exists
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )
    else:
        # Create new conversation
        title = generate_conversation_title(request.message)
        conversation = Conversation(title=title, space="default")
        db.add(conversation)
        await db.flush()  # Get ID
        # Cast to UUID since after flush, the id is populated and is a UUID instance
        # mypy sees conversation.id as Column[UUID], but at runtime it's an actual UUID
        conversation_id = cast(UUID, conversation.id)

    # Step 2: Save user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        extra_data={},
        sources=[],
    )
    db.add(user_message)
    await db.flush()

    # Step 3: RAG - Search for context if enabled
    sources = []
    context = ""

    if request.use_rag:
        embeddings_service = EmbeddingsService()
        vector_db_service = VectorDBService()

        # Generate embedding for query
        query_embedding = await embeddings_service.generate_embedding(request.message)

        # Search vector database
        search_results = await vector_db_service.search(
            query_embedding=query_embedding, limit=request.limit
        )

        sources = search_results
        context = format_context(search_results)

    # Step 4: Generate LLM response
    llm_service = LLMService()
    llm_response = await llm_service.generate_response(query=request.message, context=context)

    # Step 5: Save assistant message with sources
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=llm_response,
        extra_data={},
        sources=sources,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    # Step 6: Return response
    # Use model_validate to properly convert ORM model to Pydantic model
    message_response = MessageResponse.model_validate(assistant_message)

    # Ensure conversation_id is not None for the response
    if conversation_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversation ID should not be None at this point",
        )

    return ChatResponse(conversation_id=conversation_id, message=message_response, sources=sources)
