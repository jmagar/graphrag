"""
Database service for GraphRAG.

Provides:
- Database engine configuration
- Session management
- Database initialization
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.db.models import Base

# Create async engine
# Use SQLite for development, PostgreSQL for production
DATABASE_URL = getattr(settings, "DATABASE_URL", "sqlite+aiosqlite:///./graphrag.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG if hasattr(settings, "DEBUG") else False,
    future=True,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Initialize database by creating all tables.
    
    Should be called on application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.
    
    Usage in FastAPI:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_session)):
            # Use db session
            pass
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db() -> None:
    """
    Close database connections.
    
    Should be called on application shutdown.
    """
    await engine.dispose()
