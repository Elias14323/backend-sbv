"""Database engine and session management for the application."""

import ssl
from collections.abc import AsyncGenerator
from typing import Any

import certifi
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings


def _build_connect_args(database_url: str) -> dict[str, Any]:
    """Return asyncpg connect arguments when TLS is required."""

    if database_url.startswith("postgresql+asyncpg://"):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return {"ssl": ssl_context}
    return {}


def _build_engine() -> AsyncEngine:
    """Create the global async SQLAlchemy engine."""

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=False,
        connect_args=_build_connect_args(settings.database_url),
    )


def _build_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create the async session factory bound to the given engine."""

    return async_sessionmaker(
        engine,
        expire_on_commit=False,
    )


async_engine: AsyncEngine = _build_engine()
AsyncSessionLocal = _build_session_factory(async_engine)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""

    async with AsyncSessionLocal() as session:
        yield session


__all__ = ["async_engine", "AsyncSessionLocal", "get_db_session"]
