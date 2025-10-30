"""Tests for database models."""

import pytest
from datetime import datetime
from uuid import UUID

pytestmark = pytest.mark.asyncio


class TestConversationModel:
    """Tests for Conversation model."""

    async def test_conversation_creation(self, db_session):
        """Test creating a conversation."""
        from app.db.models import Conversation

        # Arrange
        conversation = Conversation(
            title="Test Conversation", space="work", extra_data={"test": True}
        )

        # Act
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        # Assert
        assert conversation.id is not None
        assert isinstance(conversation.id, UUID)
        assert conversation.title == "Test Conversation"
        assert conversation.space == "work"
        assert conversation.extra_data == {"test": True}
        assert isinstance(conversation.created_at, datetime)
        assert isinstance(conversation.updated_at, datetime)

    async def test_conversation_default_space(self, db_session):
        """Test conversation defaults to 'default' space."""
        from app.db.models import Conversation

        conversation = Conversation(title="Test")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        assert conversation.space == "default"

    async def test_conversation_has_messages_relationship(self, db_session):
        """Test conversation has messages relationship."""
        from app.db.models import Conversation

        conversation = Conversation(title="Test")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        assert hasattr(conversation, "messages")
        assert conversation.messages == []


class TestMessageModel:
    """Tests for Message model."""

    async def test_message_creation(self, db_session):
        """Test creating a message."""
        from app.db.models import Conversation, Message

        # Create conversation first
        conversation = Conversation(title="Test Conversation")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        # Create message
        message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Hello, world!",
            extra_data={"test": True},
            sources=[{"url": "http://example.com"}],
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        # Assert
        assert message.id is not None
        assert isinstance(message.id, UUID)
        assert message.conversation_id == conversation.id
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.extra_data == {"test": True}
        assert message.sources == [{"url": "http://example.com"}]
        assert isinstance(message.created_at, datetime)

    async def test_message_belongs_to_conversation(self, db_session):
        """Test message relationship to conversation."""
        from app.db.models import Conversation, Message

        conversation = Conversation(title="Test")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        
        message = Message(conversation_id=conversation.id, role="user", content="Test")
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        assert message.conversation is not None
        assert message.conversation.id == conversation.id

    async def test_conversation_cascade_delete_messages(self, db_session):
        """Test deleting conversation deletes its messages."""
        from app.db.models import Conversation, Message
        from sqlalchemy import select

        conversation = Conversation(title="Test")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        message = Message(conversation_id=conversation.id, role="user", content="Test")
        db_session.add(message)
        await db_session.commit()

        # Save message ID before deletion
        message_id = message.id
        
        # Delete conversation
        await db_session.delete(conversation)
        await db_session.commit()

        # Check message is also deleted
        result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        assert result.scalar_one_or_none() is None


class TestConversationTagModel:
    """Tests for ConversationTag model."""

    async def test_tag_creation(self, db_session):
        """Test creating a tag."""
        from app.db.models import Conversation, ConversationTag

        conversation = Conversation(title="Test")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        tag = ConversationTag(conversation_id=conversation.id, tag="important")
        db_session.add(tag)
        await db_session.commit()

        assert tag.conversation_id == conversation.id
        assert tag.tag == "important"

    async def test_conversation_has_tags_relationship(self, db_session):
        """Test conversation tags relationship."""
        from app.db.models import Conversation, ConversationTag

        conversation = Conversation(title="Test")
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        tag1 = ConversationTag(conversation_id=conversation.id, tag="work")
        tag2 = ConversationTag(conversation_id=conversation.id, tag="urgent")
        db_session.add_all([tag1, tag2])
        await db_session.commit()

        # Refresh to load relationship
        await db_session.refresh(conversation)

        assert len(conversation.tags) == 2
        assert any(t.tag == "work" for t in conversation.tags)
        assert any(t.tag == "urgent" for t in conversation.tags)
