"""
Conversation management API endpoints.

Provides CRUD operations for conversations and messages.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from app.db.database import get_session
from app.db.models import Conversation, Message, ConversationTag

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================


class MessageCreate(BaseModel):
    """Request model for creating a message."""

    role: str
    content: str
    extra_data: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Response model for a message."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime
    extra_data: dict
    sources: List[dict]

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""

    title: str
    space: Optional[str] = "default"
    initial_message: Optional[MessageCreate] = None


class ConversationResponse(BaseModel):
    """Response model for a conversation summary."""

    id: UUID
    title: str
    space: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    message_count: int
    last_message_preview: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationResponse):
    """Response model for detailed conversation with messages."""

    messages: List[MessageResponse]

    model_config = ConfigDict(from_attributes=True)


class ConversationUpdate(BaseModel):
    """Request model for updating a conversation."""

    title: Optional[str] = None
    tags: Optional[List[str]] = None


# ============================================================================
# Helper Functions
# ============================================================================


async def get_conversation_or_404(conversation_id: UUID, db: AsyncSession) -> Conversation:
    """Get conversation by ID or raise 404."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    return conversation


def build_conversation_response(
    conversation: Conversation, message_count: int = 0, last_message: Optional[str] = None
) -> ConversationResponse:
    """Build conversation response with computed fields."""
    tags = [tag.tag for tag in conversation.tags]

    return ConversationResponse.model_validate(
        {
            "id": conversation.id,
            "title": conversation.title,
            "space": conversation.space,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "tags": tags,
            "message_count": message_count,
            "last_message_preview": last_message,
        }
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_session)):
    """
    Create a new conversation.

    Optionally include an initial message.
    """
    # Create conversation
    conversation = Conversation(title=data.title, space=data.space)
    db.add(conversation)
    await db.flush()  # Get ID before adding message

    # Add initial message if provided
    message_count = 0
    last_message = None

    if data.initial_message:
        message = Message(
            conversation_id=conversation.id,
            role=data.initial_message.role,
            content=data.initial_message.content,
            extra_data=data.initial_message.extra_data,
        )
        db.add(message)
        message_count = 1
        last_message = data.initial_message.content

    await db.commit()
    await db.refresh(conversation)

    return build_conversation_response(conversation, message_count, last_message)


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    space: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """
    List conversations with optional filters.

    - **space**: Filter by space name
    - **tag**: Filter by tag
    - **limit**: Maximum number of results (default: 50)
    - **offset**: Number of results to skip (default: 0)
    """
    # Build base query with filters
    conv_query = select(Conversation)

    # Apply filters
    if space:
        conv_query = conv_query.where(Conversation.space == space)

    if tag:
        conv_query = conv_query.join(ConversationTag).where(ConversationTag.tag == tag)

    # Count total messages per conversation (subquery)
    msg_count_subquery = (
        select(
            Message.conversation_id,
            func.count(Message.id).label("msg_count"),
        )
        .group_by(Message.conversation_id)
        .correlate(Conversation)
        .subquery()
    )

    # Get last message per conversation (subquery with row_number)
    last_msg_subquery = (
        select(
            Message.conversation_id,
            Message.content.label("last_content"),
            func.row_number()
            .over(
                partition_by=Message.conversation_id,
                order_by=desc(Message.created_at),
            )
            .label("rn"),
        )
        .correlate(Conversation)
        .subquery()
    )

    # Main query with joins to aggregates
    conv_query = (
        conv_query.outerjoin(
            msg_count_subquery,
            Conversation.id == msg_count_subquery.c.conversation_id,
        )
        .outerjoin(
            last_msg_subquery,
            and_(
                Conversation.id == last_msg_subquery.c.conversation_id,
                last_msg_subquery.c.rn == 1,
            ),
        )
        .add_columns(
            msg_count_subquery.c.msg_count,
            last_msg_subquery.c.last_content,
        )
    )

    # Apply pagination and ordering
    conv_query = conv_query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)

    result = await db.execute(conv_query)
    rows = result.all()

    # Build responses
    responses = []
    for row in rows:
        conversation, msg_count, last_content = row[0], row[1], row[2]
        msg_count_int: int = msg_count or 0
        last_msg_content: Optional[str] = last_content
        responses.append(build_conversation_response(conversation, msg_count_int, last_msg_content))

    return responses


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_session)):
    """
    Get a single conversation with all messages.
    """
    conversation = await get_conversation_or_404(conversation_id, db)

    # Get messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = messages_result.scalars().all()

    # Build response
    tags = [tag.tag for tag in conversation.tags]
    last_preview: Optional[str] = messages[-1].content if messages else None

    return ConversationDetail.model_validate(
        {
            "id": conversation.id,
            "title": conversation.title,
            "space": conversation.space,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "tags": tags,
            "message_count": len(messages),
            "last_message_preview": last_preview,
            "messages": [MessageResponse.model_validate(m) for m in messages],
        }
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID, data: ConversationUpdate, db: AsyncSession = Depends(get_session)
):
    """
    Update conversation title and/or tags.
    """
    conversation = await get_conversation_or_404(conversation_id, db)

    # Update title if provided
    if data.title is not None:
        conversation.title = data.title

    # Update tags if provided
    if data.tags is not None:
        # Remove existing tags
        for tag in conversation.tags:
            await db.delete(tag)

        # Add new tags
        for tag_name in data.tags:
            tag = ConversationTag(conversation_id=conversation.id, tag=tag_name)
            db.add(tag)

    await db.commit()
    await db.refresh(conversation)

    # Get message count
    msg_count_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
    )
    msg_count = msg_count_result.scalar()
    msg_count_int: int = msg_count or 0  # Handle None case

    return build_conversation_response(conversation, msg_count_int)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_session)):
    """
    Delete a conversation and all its messages.
    """
    conversation = await get_conversation_or_404(conversation_id, db)

    await db.delete(conversation)
    await db.commit()


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: UUID, data: MessageCreate, db: AsyncSession = Depends(get_session)
):
    """
    Add a message to a conversation.
    """
    # Verify conversation exists
    await get_conversation_or_404(conversation_id, db)

    # Create message
    message = Message(
        conversation_id=conversation_id,
        role=data.role,
        content=data.content,
        extra_data=data.extra_data,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse.model_validate(message)
