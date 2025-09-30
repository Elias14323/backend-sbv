"""API dependencies for database sessions and common utilities."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for API endpoints."""
    async with AsyncSessionLocal() as session:
        yield session
