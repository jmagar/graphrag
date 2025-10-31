"""
Database models for GraphRAG.

Defines SQLAlchemy ORM models for:
- Conversations: Chat conversation containers
- Messages: Individual messages in conversations
- ConversationTags: Tags for organizing conversations
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Conversation(Base):
    """
    Conversation model representing a chat conversation.

    Attributes:
        id: Unique identifier (UUID)
        title: Conversation title
        space: Workspace/space name (default: "default")
        created_at: Timestamp when created
        updated_at: Timestamp when last updated
        user_id: User identifier (for future multi-user support)
        extra_data: Additional metadata (JSON)
        messages: Related messages (relationship)
        tags: Related tags (relationship)
    """

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    space = Column(String(50), default="default", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user_id = Column(String(255), nullable=True)
    extra_data = Column(JSON, default=dict, nullable=False)

    # Relationships
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )
    tags = relationship(
        "ConversationTag",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Message(Base):
    """
    Message model representing a single message in a conversation.

    Attributes:
        id: Unique identifier (UUID)
        conversation_id: Foreign key to conversation
        role: Message role ('user', 'assistant', 'system')
        content: Message content text
        created_at: Timestamp when created
        extra_data: Additional metadata (JSON)
        sources: RAG sources used for this message (JSON array)
        conversation: Related conversation (relationship)
    """

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    extra_data = Column(JSON, default=dict, nullable=False)
    sources = Column(JSON, default=list, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class ConversationTag(Base):
    """
    ConversationTag model for organizing conversations with tags.

    Attributes:
        conversation_id: Foreign key to conversation (part of composite primary key)
        tag: Tag name (part of composite primary key)
        conversation: Related conversation (relationship)
    """

    __tablename__ = "conversation_tags"

    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    tag = Column(String(50), primary_key=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="tags")
