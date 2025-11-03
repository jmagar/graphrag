"""Tests for database service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestDatabaseService:
    """Tests for database initialization and session management."""

    async def test_get_session_returns_async_session(self):
        """Test that get_session returns an AsyncSession."""
        from app.db.database import get_session

        async for session in get_session():
            assert isinstance(session, AsyncSession)
            assert session is not None

    async def test_init_db_creates_tables(self):
        """Test that init_db creates all database tables."""
        from app.db.database import init_db, engine
        from sqlalchemy import inspect

        # Initialize database
        await init_db()

        # Check that tables were created
        async with engine.connect() as conn:
            result = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
            
            assert "conversations" in result
            assert "messages" in result
            assert "conversation_tags" in result

    async def test_session_can_query_database(self):
        """Test that session can perform database operations."""
        from app.db.database import get_session, init_db
        from app.db.models import Conversation

        await init_db()

        async for session in get_session():
            # Create a conversation
            conversation = Conversation(title="Test Session")
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            # Verify it was saved
            assert conversation.id is not None

    async def test_multiple_sessions_are_independent(self):
        """Test that multiple sessions are independent."""
        from app.db.database import get_session, init_db
        from app.db.models import Conversation

        await init_db()

        # Create object in first session
        async for session1 in get_session():
            conv1 = Conversation(title="Session 1")
            session1.add(conv1)
            await session1.commit()
            await session1.refresh(conv1)
            conv1_id = conv1.id

        # Query in second session
        async for session2 in get_session():
            from sqlalchemy import select
            
            result = await session2.execute(
                select(Conversation).where(Conversation.id == conv1_id)
            )
            conv2 = result.scalar_one_or_none()
            
            assert conv2 is not None
            assert conv2.id == conv1_id
            assert conv2.title == "Session 1"
