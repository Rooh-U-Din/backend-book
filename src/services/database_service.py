"""
Database connection manager for Neon Postgres
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator, Generator
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from backend/.env
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)


class DatabaseService:
    """Manages database connections and sessions"""

    def __init__(self):
        self.database_url = os.getenv("NEON_DATABASE_URL")
        if not self.database_url:
            raise ValueError("NEON_DATABASE_URL environment variable not set")

        # Convert postgresql:// to postgresql+asyncpg:// for async support
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")

        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL logging
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True  # Verify connections before using
        )

        # Create session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions

        Usage:
            async with db_service.get_session() as session:
                result = await session.execute(query)
        """
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()


# Global database service instance
db_service: DatabaseService | None = None


def get_database_service() -> DatabaseService:
    """Get or create the global database service instance"""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service


# Sync database session for auth (FastAPI dependency)
_sync_engine = None
_sync_session_factory = None


def _get_sync_engine():
    """Get or create sync engine for auth operations"""
    global _sync_engine
    if _sync_engine is None:
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL environment variable not set")
        # Use sync driver (psycopg2)
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        _sync_engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    return _sync_engine


def _get_sync_session_factory():
    """Get or create sync session factory"""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=_get_sync_engine(),
            autocommit=False,
            autoflush=False
        )
    return _sync_session_factory


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for sync database sessions.
    Used for auth operations that require synchronous DB access.

    Usage in routes:
        @router.post("/endpoint")
        async def endpoint(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = _get_sync_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
