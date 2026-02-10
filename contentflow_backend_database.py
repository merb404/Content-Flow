# backend/app/database.py
"""
Database initialization with async SQLAlchemy.
Models are defined in models.py
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# DATABASE ENGINE & SESSION
# ============================================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    poolclass=NullPool if settings.ENVIRONMENT == "development" else None,
    connect_args={
        "timeout": 30,
        "server_settings": {
            "application_name": "contentflow_api",
            "jit": "off",  # Disable JIT for predictable performance
        },
    },
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for all ORM models
Base = declarative_base()


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for injecting database session into route handlers.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

async def init_db():
    """Create all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")


async def drop_db():
    """Drop all database tables (use with caution!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️ Database tables dropped")


async def close_db():
    """Close all database connections"""
    await engine.dispose()
    logger.info("✅ Database connections closed")
